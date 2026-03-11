package com.example.controller;

import com.example.service.PaymentService;

public class OrderController {
    
    private PaymentService paymentService = new PaymentService();
    
    public String createOrder(String productId, int quantity) {
        String orderId = generateOrderId();
        double price = calculatePrice(productId, quantity);
        return orderId;
    }
    
    public void payOrder(String orderId, double amount) {
        paymentService.processPayment(orderId, amount);
        sendConfirmation(orderId);
    }
    
    private String generateOrderId() {
        return "ORD-" + System.currentTimeMillis();
    }
    
    private double calculatePrice(String productId, int quantity) {
        return 100.0 * quantity;
    }
    
    private void sendConfirmation(String orderId) {
        System.out.println("Order confirmed: " + orderId);
    }
}
