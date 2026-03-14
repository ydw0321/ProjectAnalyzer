package com.example.service;

import com.example.dal.UserDal;
import com.example.model.User;
import com.example.util.IdGenerator;
import java.util.List;

public class UserService {
    
    private UserDal userDal = new UserDal();
    
    public User registerUser(String username, String email, String phone) {
        validateUserInfo(username, email);
        
        User existingUser = userDal.findByUsername(username);
        if (existingUser != null) {
            throw new RuntimeException("Username already exists");
        }
        
        User user = new User();
        user.setUserId(IdGenerator.generateUserId());
        user.setUsername(username);
        user.setEmail(email);
        user.setPhone(phone);
        user.setStatus("ACTIVE");
        
        userDal.insert(user);
        sendWelcomeEmail(user);
        
        return user;
    }
    
    public void updateUserProfile(String userId, String email, String phone) {
        User user = userDal.findById(userId);
        if (user == null) {
            throw new RuntimeException("User not found");
        }
        
        if (email != null) user.setEmail(email);
        if (phone != null) user.setPhone(phone);
        
        userDal.update(user);
        notifyProfileUpdated(user);
    }
    
    public List<User> getAllUsers() {
        return userDal.findAll();
    }
    
    private void validateUserInfo(String username, String email) {
        if (username == null || username.isEmpty()) {
            throw new IllegalArgumentException("Username is required");
        }
        if (email == null || !email.contains("@")) {
            throw new IllegalArgumentException("Valid email is required");
        }
    }
    
    private void sendWelcomeEmail(User user) {
        // Send email
    }
    
    private void notifyProfileUpdated(User user) {
        // Send notification
    }
}
