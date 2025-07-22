package main

import "fmt"

func main() {
    var edad int = 20
    var esMayor bool = false

    if edad >= 18 {
        fmt.Println("Es mayor de edad.")
        esMayor = true
    } else {
        fmt.Println("No es mayor de edad.")
        esMayor = false
    }
}
