package com.example.service;

import com.example.dal.OrderDal;
import com.example.model.Order;
import com.example.util.IdGenerator;
import com.example.util.DateUtil;
import java.util.Date;

public class OrderService {
    
    private OrderDal orderDal = new OrderDal();
    
    public Order createOrder(String userId, String productId, int quantity) {
        validateOrderRequest(userId, productId, quantity);
        
        Order order = new Order();
        order.setOrderId(IdGenerator.generateOrderId());
        order.setUserId(userId);
        order.setCreatedAt(new Date());
        order.setUpdatedAt(new Date());
        
        orderDal.insert(order);
        notifyOrderCreated(order);
        
        return order;
    }
    
    public void cancelOrder(String orderId) {
        Order order = orderDal.findById(orderId);
        if (order == null) {
            throw new RuntimeException("Order not found");
        }
        
        if ("PAID".equals(order.getStatus())) {
            processRefund(orderId);
        }
        
        order.setStatus("CANCELLED");
        order.setUpdatedAt(new Date());
        orderDal.update(order);
    }
    
    private void validateOrderRequest(String userId, String productId, int quantity) {
        if (userId == null || userId.isEmpty()) {
            throw new IllegalArgumentException("User ID is required");
        }
        if (quantity <= 0) {
            throw new IllegalArgumentException("Quantity must be positive");
        }
    }
    
    private void notifyOrderCreated(Order order) {
        // Send notification
    }
    
    private void processRefund(String orderId) {
        // Process refund logic
    }
}
