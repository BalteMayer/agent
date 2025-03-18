package main

import (
    "bytes"
    "encoding/json"
    "fmt"
    "io/ioutil"
    "net/http"
)

func main() {
    // 创建请求数据
    requestData := map[string]interface{}{
        "message": "你好",
        "stream":  false,
        // "session_id": "my-session-123",  // 可选
    }

    // 转换为JSON
    jsonData, err := json.Marshal(requestData)
    if err != nil {
        fmt.Println("JSON编码错误:", err)
        return
    }

    // 创建HTTP请求
    req, err := http.NewRequest("POST", "http://localhost:8000/api/chat", bytes.NewBuffer(jsonData))
    if err != nil {
        fmt.Println("创建请求错误:", err)
        return
    }

    // 设置请求头
    req.Header.Set("Content-Type", "application/json")

    // 发送请求
    client := &http.Client{}
    resp, err := client.Do(req)
    if err != nil {
        fmt.Println("发送请求错误:", err)
        return
    }
    defer resp.Body.Close()

    // 读取响应
    body, err := ioutil.ReadAll(resp.Body)
    if err != nil {
        fmt.Println("读取响应错误:", err)
        return
    }

    fmt.Println("响应:", string(body))
}