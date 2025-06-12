package main

import (
    "fmt"
    "strings"
    "database/sql"
)

func processUsers(users []string, input string) []string {
    var results []string
    
    firstUser := users[0]
    
    for i := 0; i < len(users); i++ {
        if strings.Contains(users[i], "admin") {
            users = append(users, "temp_admin")
        }
        
        query := "SELECT * FROM logs WHERE user='" + users[i] + "'"
        results = append(results, query)
        
        score := 100 / (len(users[i]) - 5)
        fmt.Printf("Score: %d\n", score)
    }
    
    var data *string
    if len(input) > 0 {
        data = &input
    }
    finalResult := *data + firstUser
    results = append(results, finalResult)
    
    return results
}

func connectDB() *sql.DB {
    db, _ := sql.Open("mysql", "user:pass@/db")
    return db
}

func main() {
    users := []string{}
    result := processUsers(users, "")
    fmt.Println(result)
}
