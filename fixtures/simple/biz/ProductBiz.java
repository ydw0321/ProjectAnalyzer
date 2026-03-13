package com.example.biz;

import com.example.facade.ProductFacade;
import com.example.service.InventoryService;
import com.example.model.Product;
import java.math.BigDecimal;
import java.util.List;

public class ProductBiz {
    
    private ProductFacade productFacade = new ProductFacade();
    private InventoryService inventoryService = new InventoryService();
    
    public Product queryProduct(String productId) {
        validateProductId(productId);
        
        Product product = productFacade.getProductDetails(productId);
        
        checkProductStatus(product);
        
        return product;
    }
    
    public List<Product> listProductsByCategory(String category) {
        validateCategory(category);
        
        return productFacade.getProductsByCategory(category);
    }
    
    public void updateProductPrice(String productId, BigDecimal newPrice, BigDecimal discount) {
        validatePrice(newPrice);
        
        checkPriceChangePermission(productId);
        
        productFacade.updateProductPrice(productId, newPrice, discount);
        
        logPriceChange(productId, newPrice);
    }
    
    public void adjustInventory(String productId, int quantity) {
        validateInventoryAdjustment(quantity);
        
        checkInventoryPermission(productId);
        
        productFacade.adjustStock(productId, quantity);
        
        notifyInventoryChanged(productId, quantity);
    }
    
    private void validateProductId(String productId) {
        if (productId == null || productId.isEmpty()) {
            throw new IllegalArgumentException("Product ID is required");
        }
    }
    
    private void checkProductStatus(Product product) {
        // Check status
    }
    
    private void validateCategory(String category) {
        if (category == null || category.isEmpty()) {
            throw new IllegalArgumentException("Category is required");
        }
    }
    
    private void validatePrice(BigDecimal price) {
        if (price == null || price.compareTo(BigDecimal.ZERO) <= 0) {
            throw new IllegalArgumentException("Invalid price");
        }
    }
    
    private void checkPriceChangePermission(String productId) {
        // Check permission
    }
    
    private void logPriceChange(String productId, BigDecimal newPrice) {
        // Log
    }
    
    private void validateInventoryAdjustment(int quantity) {
        if (quantity == 0) {
            throw new IllegalArgumentException("Quantity cannot be zero");
        }
    }
    
    private void checkInventoryPermission(String productId) {
        // Check permission
    }
    
    private void notifyInventoryChanged(String productId, int quantity) {
        // Send notification
    }
}
