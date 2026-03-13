package com.example.util;

import java.util.UUID;

public class IdGenerator {
    
    public static String generateOrderId() {
        return "ORD-" + UUID.randomUUID().toString();
    }
    
    public static String generateUserId() {
        return "USR-" + UUID.randomUUID().toString();
    }
    
    public static String generateProductId() {
        return "PRD-" + UUID.randomUUID().toString();
    }
    
    public static String generateTransactionId() {
        return "TXN-" + System.currentTimeMillis() + "-" + UUID.randomUUID().toString().substring(0, 8);
    }
}
