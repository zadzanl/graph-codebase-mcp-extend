// Sample JavaScript file for testing
function calculateTotal(items, taxRate) {
    return items.reduce((sum, item) => sum + item.price, 0) * (1 + taxRate);
}

const formatDate = (date, format) => {
    return date.toLocaleDateString('en-US', { format });
};

class User {
    constructor(name, email) {
        this.name = name;
        this.email = email;
    }

    getDisplayName() {
        return `${this.name} <${this.email}>`;
    }
}

class AdminUser extends User {
    constructor(name, email, role) {
        super(name, email);
        this.role = role;
    }

    hasPermission(permission) {
        return this.role === 'admin';
    }
}

const API_URL = 'https://api.example.com';
let activeUsers = 0;
var legacyFlag = true;

export { calculateTotal, formatDate, User, AdminUser };
export default API_URL;
