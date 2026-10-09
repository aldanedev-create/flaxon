package main
import ("encoding/json"; "net/http"; "os"; "runtime")
func main() {
 runtime.GOMAXPROCS(1)
 http.HandleFunc("/plaintext", func(w http.ResponseWriter,r *http.Request) {
  w.Header().Set("Content-Type", "text/plain; charset=utf-8")
  w.Header().Set("Content-Length", "13")
  w.Write([]byte("Hello, World!"))
 })
 http.HandleFunc("/json",func(w http.ResponseWriter,r *http.Request) {
  body,_:=json.Marshal(map[string]string{"message":"Hello, World!"})
  w.Header().Set("Content-Type","application/json")
  w.Write(body)
 })
 if err:=http.ListenAndServe("127.0.0.1:"+os.Getenv("PORT"),nil);err!=nil {panic(err)}
}
