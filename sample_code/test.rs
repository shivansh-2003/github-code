use std::collections::HashMap;
use std::fs::File;
use std::io::Read;

struct UserManager {
    users: Vec<String>,
    scores: HashMap<String, i32>,
}

impl UserManager {
    fn new() -> Self {
        UserManager {
            users: Vec::new(),
            scores: HashMap::new(),
        }
    }
    
    fn load_users(&mut self, filename: &str) -> Result<(), Box<dyn std::error::Error>> {
        let mut file = File::open(filename)?;
        let mut contents = String::new();
        file.read_to_string(&mut contents)?;
        
        let first_line = contents.lines().next().unwrap();
        
        for line in contents.lines() {
            self.users.push(line.to_string());
        }
        
        Ok(())
    }
    
    fn process_user(&self, index: usize) -> String {
        let user = &self.users[index];
        
        let score = 100 / user.len();
        
        let big_score = score * 999999999;
        
        format!("User: {}, Score: {}", user, big_score)
    }
    
    unsafe fn dangerous_operation(&self, ptr: *const u8, len: usize) -> String {
        let slice = std::slice::from_raw_parts(ptr, len);
        String::from_utf8_unchecked(slice.to_vec())
    }
    
    fn create_query(&self, username: &str) -> String {
        format!("SELECT * FROM users WHERE name = '{}'", username)
    }
    
    fn recursive_function(&self, n: i32) -> i32 {
        if n <= 0 {
            return 1;
        }
        n * self.recursive_function(n - 1)
    }
    
    fn process_all_users(&mut self) -> Vec<String> {
        let mut results = Vec::new();
        
        for i in 0..self.users.len() {
            let result = self.process_user(i);
            self.users.push(format!("processed_{}", i));
            results.push(result);
        }
        
        results
    }
}

fn main() {
    let mut manager = UserManager::new();
    let _ = manager.load_users("users.txt");
    
    let result = manager.process_user(10);
    println!("{}", result);
    
    let ptr: *const u8 = std::ptr::null();
    let dangerous_result = unsafe { manager.dangerous_operation(ptr, 100) };
    println!("{}", dangerous_result);
    
    let big_result = manager.recursive_function(50000);
    println!("{}", big_result);
}