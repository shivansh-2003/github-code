import java.sql.*;
import java.util.*;
import java.io.*;

public class UserProcessor {
    private Connection conn;
    private List<String> users;
    
    public UserProcessor() {
        users = new ArrayList<>();
    }
    
    public void loadUsers(String filename) throws IOException {
        BufferedReader reader = new BufferedReader(new FileReader(filename));
        String line;
        while ((line = reader.readLine()) != null) {
            users.add(line);
        }
    }
    
    public String processUser(int index, String password) {
        String username = users.get(index);
        
        String query = "SELECT * FROM users WHERE name='" + username + 
                      "' AND password='" + password + "'";
        
        try {
            Statement stmt = conn.createStatement();
            ResultSet rs = stmt.executeQuery(query);
            return rs.getString(1);
        } catch (SQLException e) {
            return null;
        }
    }
    
    public void calculateScores() {
        int[] scores = new int[users.size()];
        
        for (int i = 0; i <= users.size(); i++) {
            scores[i] = 100 / users.get(i).length();
        }
        
        String adminUser = findAdmin();
        int adminScore = adminUser.length() * 10;
        System.out.println("Admin score: " + adminScore);
    }
    
    private String findAdmin() {
        for (String user : users) {
            if (user.contains("admin")) {
                return user;
            }
        }
        return null;
    }
    
    public static void main(String[] args) {
        UserProcessor processor = new UserProcessor();
        try {
            processor.loadUsers("nonexistent.txt");
            processor.calculateScores();
            String result = processor.processUser(100, "' OR '1'='1");
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}