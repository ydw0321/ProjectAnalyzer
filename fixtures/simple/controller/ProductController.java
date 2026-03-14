package com.example.controller;

import com.example.biz.ProductBiz;
import com.example.model.Product;
import java.math.BigDecimal;
import java.util.List;

public class ProductController {
    
    private ProductBiz productBiz = new ProductBiz();
    
    public String getProduct(String productId) {
        try {
            Product product = productBiz.queryProduct(productId);
            return buildSuccessResponse(product.getName());
        } catch (Exception e) {
            return buildErrorResponse(e.getMessage());
        }
    }
    
    public String listProducts(String category) {
        try {
            List<Product> products = productBiz.listProductsByCategory(category);
            return buildSuccessResponse("Found " + products.size() + " products");
        } catch (Exception e) {
            return buildErrorResponse(e.getMessage());
        }
    }
    
    public String updatePrice(String productId, BigDecimal newPrice) {
        try {
            productBiz.updateProductPrice(productId, newPrice, null);
            return buildSuccessResponse("Price updated");
        } catch (Exception e) {
            return buildErrorResponse(e.getMessage());
        }
    }
    
    public String adjustStock(String productId, int quantity) {
        try {
            productBiz.adjustInventory(productId, quantity);
            return buildSuccessResponse("Stock adjusted");
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
