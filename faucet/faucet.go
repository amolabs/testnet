package main

import (
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"os"

	"github.com/amolabs/amo-client-go/lib/keys"
	"github.com/amolabs/amo-client-go/lib/rpc"
	"github.com/gin-gonic/gin"
	"github.com/gin-gonic/gin/binding"
)

// default settings
const (
	DefaultAppName           = "AMO faucet"
	DefaultQueueSize         = 3
	DefaultListeAddr         = "0.0.0.0:2000"
	DefaultRPCRemote         = "172.105.213.114:26657"
	DefaultTxBroadcastOption = "commit"
	DefaultFaucetAmount      = "1000"
)

func printLog(logs ...string) {
	fmt.Printf("[%s] ", DefaultAppName)
	for i, log := range logs {
		if i%2 == 0 {
			fmt.Printf("%s=", log)
		} else {
			fmt.Printf("%s", log)
			if i != len(logs)-1 {
				fmt.Printf(", ")
			}
		}
	}
	fmt.Printf("\n")
}

func printError(err error) {
	fmt.Printf("[%s] Error: %s\n", DefaultAppName, err.Error())
}

func printErrorAndExit(err error) {
	printError(err)
	os.Exit(1)
}

type WaitQueue struct {
	addrs []string
	size  int
}

func NewWaitQueue(size int) (*WaitQueue, error) {
	if size == 0 {
		return nil, fmt.Errorf("size should be over 0")
	}
	return &WaitQueue{
		addrs: []string{},
		size:  size,
	}, nil
}

func (wq *WaitQueue) Push(newAddr string) {
	// pop
	if len(wq.addrs) == wq.size {
		wq.addrs = wq.addrs[1:]
	}

	// push
	wq.addrs = append(wq.addrs, newAddr)
}

func (wq *WaitQueue) Exist(targetAddr string) bool {
	for _, addr := range wq.addrs {
		if addr == targetAddr {
			return true
		}
	}
	return false
}

func main() {
	// prepare flags
	qs := flag.Int("qsize", DefaultQueueSize, "size of wait queue")
	la := flag.String("listen", DefaultListeAddr, "<listen_address>:<listen_port>")
	rr := flag.String("rpc", DefaultRPCRemote, "<rpc_address>:<rpc_port>")
	tb := flag.String("broadcast", DefaultTxBroadcastOption, "<commit | sync | async>")
	fa := flag.String("amount", DefaultFaucetAmount, "faucet amount")
	pk := flag.String("key", "", "hex or base64 encoded faucet private key")

	flag.Parse()

	// prepare key
	if *pk == "" {
		err := fmt.Errorf("no specified private key")
		printErrorAndExit(err)
	}
	var pkb []byte
	pkb, err := hex.DecodeString(*pk)
	if err != nil {
		pkb, err = base64.StdEncoding.DecodeString(*pk)
		if err != nil {
			printErrorAndExit(err)
		}
	}
	key, err := keys.ImportKey(pkb, nil, false)
	if err != nil {
		printErrorAndExit(err)
	}

	// prepare rpc
	rpc.RpcRemote = "http://" + *rr
	rpc.TxBroadcastOption = *tb

	// prepaer waitQueue
	wq, err := NewWaitQueue(*qs)
	if err != nil {
		printErrorAndExit(err)
	}

	gin.SetMode(gin.ReleaseMode)
	r := gin.Default()
	r.POST("", func(c *gin.Context) {
		var reqData struct {
			Recp string `json:"recp"`
		}
		err := c.MustBindWith(&reqData, binding.JSON)
		if err != nil {
			printError(err)
			c.String(500, err.Error())
			return
		}
		if reqData.Recp == "" {
			err := fmt.Errorf("received empty recp")
			printError(err)
			c.String(500, err.Error())
			return
		}

		if wq.Exist(reqData.Recp) {
			err := fmt.Errorf("%s already in wait queue", reqData.Recp)
			printError(err)
			c.String(409, err.Error())
			return
		}

		rawMsg, err := rpc.NodeStatus()
		if err != nil {
			printError(err)
			err = fmt.Errorf("internal error")
			c.String(500, err.Error())
			return
		}
		jsonMsg, err := json.Marshal(rawMsg.SyncInfo)
		if err != nil {
			printError(err)
			err = fmt.Errorf("internal error")
			c.String(500, err.Error())
			return
		}
		data := make(map[string]interface{})
		err = json.Unmarshal(jsonMsg, &data)
		if err != nil {
			printError(err)
			err = fmt.Errorf("internal error")
			c.String(500, err.Error())
			return
		}
		lastHeight := data["latest_block_height"].(string)
		if lastHeight == "0" {
			err := fmt.Errorf("improper last_height")
			printError(err)
			err = fmt.Errorf("internal error")
			c.String(500, err.Error())
			return
		}

		printLog("tx", "transfer", "from", key.Address, "to", reqData.Recp, "amount", *fa)
		result, err := rpc.Transfer(0, reqData.Recp, *fa, *key, "0", lastHeight)
		if err != nil {
			printError(err)
			err = fmt.Errorf("internal error")
			c.String(500, err.Error())
			return
		}

		wq.Push(reqData.Recp)

		resultJSON, err := json.Marshal(result)
		if err != nil {
			printError(err)
			return
		}
		printLog("tx", "transfer", "result", string(resultJSON))
		c.String(200, "successfully transfered %s to %s", *fa, reqData.Recp)
	})

	r.Run(*la)
}
