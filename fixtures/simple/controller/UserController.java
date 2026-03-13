package com.example.controller;

import com.example.biz.UserBiz;
import com.example.model.User;
import java.util.List;

public class UserController {
    
    private UserBiz userBiz = new UserBiz();
    
    public String register(String username, String email, String phone) {
        try {
            User user = userBiz.registerUser(username, email, phone);
            return buildSuccessResponse(user.getUserId());
        } catch (Exception e) {
            return buildErrorResponse(e.getMessage());
        }
    }
    
    public String updateProfile(String userId, String email, String phone) {
        try {
            userBiz.modifyUserProfile(userId, email, phone);
            return buildSuccessResponse("Profile updated");
        } catch (Exception e) {
            return buildErrorResponse(e.getMessage());
        }
    }
    
    public String listUsers() {
        try {
            List<User> users = userBiz.fetchAllUsers();
            return buildSuccessResponse("Found " + users.size() + " users");
        } catch (Exception e) {
            return buildErrorResponse(e.getMessage());
        }
    }
    
    private String buildSuccessResponse(String data) {
        return "{\"status\":\"success\",\"data\":\"" + data + "\"}";
    }
    
    private String buildErrorResponse(String message) {
        return "{\"status\":\"error\",\"message\":\"" + message + "\"}";
    }
}
