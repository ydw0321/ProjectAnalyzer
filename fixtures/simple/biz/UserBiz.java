package com.example.biz;

import com.example.facade.UserFacade;
import com.example.model.User;
import java.util.List;

public class UserBiz {
    
    private UserFacade userFacade = new UserFacade();
    
    public User registerUser(String username, String email, String phone) {
        validateRegistration(username, email);
        
        checkUsernameAvailability(username);
        
        checkEmailFormat(email);
        
        User user = userFacade.register(username, email, phone);
        
        logUserRegistration(user);
        
        return user;
    }
    
    public void modifyUserProfile(String userId, String email, String phone) {
        validateUserId(userId);
        
        checkUserExists(userId);
        
        if (email != null) {
            checkEmailFormat(email);
        }
        
        userFacade.updateProfile(userId, email, phone);
        
        logProfileModification(userId);
    }
    
    public List<User> fetchAllUsers() {
        checkAdminPermission();
        
        return userFacade.getAllUsers();
    }
    
    private void validateRegistration(String username, String email) {
        if (username == null || username.length() < 3) {
            throw new IllegalArgumentException("Username must be at least 3 characters");
        }
    }
    
    private void checkUsernameAvailability(String username) {
        // Check availability
    }
    
    private void checkEmailFormat(String email) {
        if (email == null || !email.contains("@")) {
            throw new IllegalArgumentException("Invalid email format");
        }
    }
    
    private void logUserRegistration(User user) {
        // Log
    }
    
    private void validateUserId(String userId) {
        if (userId == null || userId.isEmpty()) {
            throw new IllegalArgumentException("User ID is required");
        }
    }
    
    private void checkUserExists(String userId) {
        // Check if user exists
    }
    
    private void logProfileModification(String userId) {
        // Log
    }
    
    private void checkAdminPermission() {
        // Check permission
    }
}
