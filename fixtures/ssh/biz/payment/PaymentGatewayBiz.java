package com.legacy.ssh.biz.payment;

import com.legacy.ssh.interceptor.RetryInterceptor;
import com.legacy.ssh.legacy.integration.LegacyRpcClient;
import com.legacy.ssh.legacy.integration.ServiceLocator;
import com.legacy.ssh.model.order.Order;
import com.legacy.ssh.service.PaymentService;
import com.legacy.ssh.service.impl.payment.LegacyPaymentServiceImpl;
import com.legacy.ssh.util.cache.CacheUtil;
import com.legacy.ssh.util.common.LegacyCodeUtil;

public class PaymentGatewayBiz {

    private PaymentService paymentService = new LegacyPaymentServiceImpl();
    private RetryInterceptor retryInterceptor = new RetryInterceptor();
    private LegacyRpcClient legacyRpcClient = new LegacyRpcClient();

    public String processPayment(Order order) {
        if (order == null) {
            return "FAIL:NULL_ORDER";
        }

        String channel = CacheUtil.get("channel.default");
        if (channel != null && channel.length() > 0) {
            order.setPaymentChannel(channel);
            if ("ALIPAY".equals(channel) || "WECHAT".equals(channel)) {
                paymentService = ServiceLocator.getPaymentService("ALIPAY".equals(channel) ? "ALI" : "WX");
            }
        }

        String paymentNo = paymentService.pay(order);
        legacyRpcClient.post("legacy-payment-log", paymentNo);
        LegacyCodeUtil.debug("paymentNo=" + paymentNo);

        if (paymentNo == null || paymentNo.startsWith("FAIL")) {
            retryInterceptor.doRetry(order.getOrderId());
            return "WAIT_RETRY";
        }

        return paymentNo;
    }

    public boolean reversePayment(Order order) {
        return paymentService.reverse(order);
    }
}
