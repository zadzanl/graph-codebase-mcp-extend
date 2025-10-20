// Simple Java test file
import java.util.List;
import java.util.ArrayList;

public class Person {
    private String name;
    private int age;
    
    public Person(String name, int age) {
        this.name = name;
        this.age = age;
    }
    
    public String getName() {
        return this.name;
    }
    
    public void setName(String name) {
        this.name = name;
    }
    
    public int getAge() {
        return this.age;
    }
}

class Helper {
    public static void printMessage(String message) {
        System.out.println(message);
    }
}
