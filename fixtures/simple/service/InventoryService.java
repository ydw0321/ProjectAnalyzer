package com.example.service;

import com.example.dal.ProductDal;
import com.example.model.Product;

public class InventoryService {
    
    private ProductDal productDal = new ProductDal();
    
    public boolean checkStock(String productId, int requiredQuantity) {
        Product product = productDal.findById(productId);
        if (product == null) {
            return false;
        }
        return product.getStock() >= requiredQuantity;
    }
    
    public void reserveStock(String productId, int quantity) {
        if (!checkStock(productId, quantity)) {
            throw new RuntimeException("Insufficient stock");
        }
        
        Product product = productDal.findById(productId);
        productDal.updateStock(productId, -quantity);
        notifyStockReserved(productId, quantity);
    }
    
    public void releaseStock(String productId, int quantity) {
        Product product = productDal.findById(productId);
        productDal.updateStock(productId, quantity);
        notifyStockReleased(productId, quantity);
    }
    
    private void notifyStockReserved(String productId, int quantity) {
        // Send notification
    }
    
    private void notifyStockReleased(String productId, int quantity) {
        // Send notification
    }
}
