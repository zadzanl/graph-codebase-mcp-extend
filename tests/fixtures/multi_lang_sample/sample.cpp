// Simple C++ test file
#include <iostream>
#include <string>

class Person {
private:
    std::string name;
    int age;
    
public:
    Person(std::string n, int a) : name(n), age(a) {}
    
    std::string getName() {
        return name;
    }
    
    void setName(std::string n) {
        name = n;
    }
    
    int getAge() {
        return age;
    }
};

void printMessage(std::string message) {
    std::cout << message << std::endl;
}

int add(int a, int b) {
    return a + b;
}
