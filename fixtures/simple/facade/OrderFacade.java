package com.example.facade;

import com.example.service.OrderService;
import com.example.service.ProductService;
import com.example.service.PaymentService;
import com.example.service.InventoryService;
import com.example.model.Order;
import com.example.model.Product;
import com.example.util.PriceCalculator;
import java.math.BigDecimal;

public class OrderFacade {
    
    private OrderService orderService = new OrderService();
    private ProductService productService = new ProductService();
    private PaymentService paymentService = new PaymentService();
    private InventoryService inventoryService = new InventoryService();
    
    public Order placeOrder(String userId, String productId, int quantity, String paymentMethod) {
        Product product = productService.getProduct(productId);
        
        boolean stockAvailable = inventoryService.checkStock(productId, quantity);
        if (!stockAvailable) {
            throw new RuntimeException("Product out of stock");
        }
        
        inventoryService.reserveStock(productId, quantity);
        
        try {
            BigDecimal price = productService.calculateProductPrice(productId, null);
            BigDecimal totalAmount = PriceCalculator.calculateTotal(price.multiply(BigDecimal.valueOf(quantity)), null, null);
            
            String transactionId = paymentService.processPayment(null, totalAmount, paymentMethod);
            
            Order order = orderService.createOrder(userId, productId, quantity);
            confirmOrder(order, transactionId);
            
            return order;
        } catch (Exception e) {
            inventoryService.releaseStock(productId, quantity);
            throw new RuntimeException("Order failed: " + e.getMessage());
        }
    }
    
    public void cancelOrder(String orderId) {
        orderService.cancelOrder(orderId);
    }
    
    private void confirmOrder(Order order, String transactionId) {
        // Confirm order
    }
}
