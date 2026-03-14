package com.example.util;

import java.math.BigDecimal;
import java.math.RoundingMode;

public class PriceCalculator {
    
    public static BigDecimal calculateDiscount(BigDecimal originalPrice, BigDecimal discountRate) {
        if (discountRate == null || discountRate.compareTo(BigDecimal.ZERO) < 0) {
            return originalPrice;
        }
        BigDecimal discount = originalPrice.multiply(discountRate).divide(BigDecimal.valueOf(100), 2, RoundingMode.HALF_UP);
        return originalPrice.subtract(discount);
    }
    
    public static BigDecimal calculateTax(BigDecimal amount, BigDecimal taxRate) {
        if (taxRate == null || amount == null) {
            return BigDecimal.ZERO;
        }
        return amount.multiply(taxRate).divide(BigDecimal.valueOf(100), 2, RoundingMode.HALF_UP);
    }
    
    public static BigDecimal calculateTotal(BigDecimal subtotal, BigDecimal tax, BigDecimal shippingFee) {
        BigDecimal total = subtotal;
        if (tax != null) total = total.add(tax);
        if (shippingFee != null) total = total.add(shippingFee);
        return total.setScale(2, RoundingMode.HALF_UP);
    }
}
