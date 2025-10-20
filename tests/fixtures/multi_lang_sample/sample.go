// Simple Go test file
package main

import (
	"fmt"
)

type Person struct {
	Name string
	Age  int
}

func NewPerson(name string, age int) *Person {
	return &Person{
		Name: name,
		Age:  age,
	}
}

func (p *Person) GetName() string {
	return p.Name
}

func (p *Person) SetName(name string) {
	p.Name = name
}

func (p *Person) GetAge() int {
	return p.Age
}

func Greet(name string) {
	fmt.Printf("Hello, %s!\n", name)
}

func Add(a, b int) int {
	return a + b
}
