package main

import "fmt"

func main() {
    var x int = true       // ❌ Tipo incorrecto
    var y bool = 42        // ❌ Tipo incorrecto
    z = 10                 // ❌ No declarada
    var a int = 10
    var a bool = false     // ❌ Redeclaración
    if 5 { }               // ❌ Condición no bool
    for x { }              // ❌ x es int, no bool
}