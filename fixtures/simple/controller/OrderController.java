package com.example.controller;

import com.example.biz.OrderBiz;
import com.example.model.Order;
import com.example.util.IdGenerator;

public class OrderController {
    
    private OrderBiz orderBiz = new OrderBiz();
    
    public String createOrder(String userId, String productId, int quantity, String paymentMethod) {
        try {
            Order order = orderBiz.submitOrder(userId, productId, quantity, paymentMethod);
            return buildSuccessResponse(order.getOrderId());
        } catch (Exception e) {
            return buildErrorResponse(e.getMessage());
        }
    }
    
    public String cancelOrder(String orderId) {
        try {
            orderBiz.handleOrderCancellation(orderId);
            return buildSuccessResponse("Order cancelled");
        } catch (Exception e) {
            return buildErrorResponse(e.getMessage());
        }
    }
    
    public String queryOrder(String orderId) {
        if (orderId == null || orderId.isEmpty()) {
            return buildErrorResponse("Order ID is required");
        }
        
        return buildSuccessResponse("Order details");
    }
    
    private String buildSuccessResponse(String data) {
        return "{\"status\":\"success\",\"data\":\"" + data + "\"}";
    }
    
    private String buildErrorResponse(String message) {
        return "{\"status\":\"error\",\"message\":\"" + message + "\"}";
    }
}
