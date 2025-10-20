// Sample TypeScript file with type annotations

// Interface (compile-time only, not parsed)
interface User {
    id: number;
    name: string;
    email: string;
}

// Type alias (compile-time only, not parsed)
type Status = 'active' | 'inactive' | 'pending';

// Function with type annotations
function createUser(name: string, email: string): User {
    return {
        id: Math.random(),
        name: name,
        email: email
    };
}

// Arrow function with types
const validateEmail = (email: string): boolean => {
    return email.includes('@');
};

// Generic function
function identity<T>(arg: T): T {
    return arg;
}

// Class with typed properties and methods
class UserService {
    private users: User[] = [];
    
    addUser(user: User): void {
        this.users.push(user);
    }
    
    findUser(id: number): User | undefined {
        return this.users.find(u => u.id === id);
    }
    
    async fetchUsers(): Promise<User[]> {
        // Simulated async operation
        return this.users;
    }
}

// Const with type annotation
const MAX_USERS: number = 100;
