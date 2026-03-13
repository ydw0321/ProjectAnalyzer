package com.example.service;

import com.example.dal.ProductDal;
import com.example.model.Product;
import com.example.util.PriceCalculator;
import java.math.BigDecimal;
import java.util.List;

public class ProductService {
    
    private ProductDal productDal = new ProductDal();
    
    public Product getProduct(String productId) {
        Product product = productDal.findById(productId);
        if (product == null) {
            throw new RuntimeException("Product not found: " + productId);
        }
        return product;
    }
    
    public List<Product> getProductsByCategory(String category) {
        validateCategory(category);
        return productDal.findByCategory(category);
    }
    
    public void updateStock(String productId, int quantity) {
        Product product = getProduct(productId);
        int newStock = product.getStock() + quantity;
        
        if (newStock < 0) {
            throw new RuntimeException("Insufficient stock");
        }
        
        productDal.updateStock(productId, quantity);
        notifyStockChanged(productId, newStock);
    }
    
    public BigDecimal calculateProductPrice(String productId, BigDecimal discountRate) {
        Product product = getProduct(productId);
        return PriceCalculator.calculateDiscount(product.getPrice(), discountRate);
    }
    
    private void validateCategory(String category) {
        if (category == null || category.isEmpty()) {
            throw new IllegalArgumentException("Category is required");
        }
    }
    
    private void notifyStockChanged(String productId, int newStock) {
        // Send notification
    }
}
