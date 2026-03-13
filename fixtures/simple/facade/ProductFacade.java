package com.example.facade;

import com.example.service.ProductService;
import com.example.service.InventoryService;
import com.example.model.Product;
import com.example.util.PriceCalculator;
import java.math.BigDecimal;
import java.util.List;

public class ProductFacade {
    
    private ProductService productService = new ProductService();
    private InventoryService inventoryService = new InventoryService();
    
    public Product getProductDetails(String productId) {
        return productService.getProduct(productId);
    }
    
    public List<Product> getProductsByCategory(String category) {
        return productService.getProductsByCategory(category);
    }
    
    public void updateProductPrice(String productId, BigDecimal newPrice, BigDecimal discountRate) {
        Product product = productService.getProduct(productId);
        
        BigDecimal finalPrice = PriceCalculator.calculateDiscount(newPrice, discountRate);
        
        product.setPrice(finalPrice);
    }
    
    public void adjustStock(String productId, int quantity) {
        boolean hasStock = inventoryService.checkStock(productId, Math.abs(quantity));
        
        if (quantity < 0 && !hasStock) {
            throw new RuntimeException("Cannot reduce stock");
        }
        
        inventoryService.reserveStock(productId, quantity);
    }
    
    public BigDecimal calculateFinalPrice(String productId, BigDecimal discountRate) {
        return productService.calculateProductPrice(productId, discountRate);
    }
}
