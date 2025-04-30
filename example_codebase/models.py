from utils import log_execution

class Person:
    species = "Homo sapiens"

    def __init__(self, name):
        self.name = name

    def greet(self):
        return f"Hello, I am {self.name}"

class Employee(Person):
    def __init__(self, name, position):
        super().__init__(name)
        self.position = position

    @log_execution
    def work(self):
        return f"{self.name} works as a {self.position}"

    def __str__(self):
        return f"{self.name} ({self.position})" 