package com.example.facade;

import com.example.service.UserService;
import com.example.model.User;
import java.util.List;

public class UserFacade {
    
    private UserService userService = new UserService();
    
    public User register(String username, String email, String phone) {
        validateRegistrationInput(username, email);
        
        User user = userService.registerUser(username, email, phone);
        
        sendConfirmation(user);
        
        return user;
    }
    
    public void updateProfile(String userId, String email, String phone) {
        User user = userService.getAllUsers().stream()
            .filter(u -> u.getUserId().equals(userId))
            .findFirst()
            .orElse(null);
        
        if (user == null) {
            throw new RuntimeException("User not found");
        }
        
        userService.updateUserProfile(userId, email, phone);
    }
    
    public List<User> getAllUsers() {
        return userService.getAllUsers();
    }
    
    private void validateRegistrationInput(String username, String email) {
        if (username == null || username.length() < 3) {
            throw new IllegalArgumentException("Username must be at least 3 characters");
        }
    }
    
    private void sendConfirmation(User user) {
        // Send confirmation
    }
}
