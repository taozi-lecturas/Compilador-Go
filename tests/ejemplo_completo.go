package main

import "fmt"

func main() {
    var a int = 10
    var b int = 1
    var c int = 0

    for b < a {
        b = b + 1
        if b % 2 == 0 {
            c = c + b
        }
    }

    fmt.Print("Suma de pares: ")
    fmt.Println(c)
}
