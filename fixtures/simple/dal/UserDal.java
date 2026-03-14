package com.example.dal;

import com.example.model.User;
import java.util.ArrayList;
import java.util.List;

public class UserDal {
    
    public User findById(String userId) {
        return new User();
    }
    
    public User findByUsername(String username) {
        return new User();
    }
    
    public void insert(User user) {
        // Insert into database
    }
    
    public void update(User user) {
        // Update database
    }
    
    public List<User> findAll() {
        return new ArrayList<>();
    }
}
