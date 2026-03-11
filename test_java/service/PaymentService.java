package com.example.service;

public class PaymentService {
    
    public void processPayment(String orderId, double amount) {
        validatePayment(orderId, amount);
        invokePaymentGateway(orderId, amount);
        updateOrderStatus(orderId);
    }
    
    private void validatePayment(String orderId, double amount) {
        if (amount <= 0) {
            throw new IllegalArgumentException("Invalid amount");
        }
    }
    
    private void invokePaymentGateway(String orderId, double amount) {
        // Call external payment API
        System.out.println("Processing payment for order: " + orderId);
    }
    
    private void updateOrderStatus(String orderId) {
        // Update order status in database
    }
    
    public boolean refundPayment(String orderId) {
        return processRefund(orderId);
    }
    
    private boolean processRefund(String orderId) {
        return true;
    }
}
