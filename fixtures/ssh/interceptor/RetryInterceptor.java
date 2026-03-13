package com.legacy.ssh.interceptor;

import com.legacy.ssh.service.impl.order.OrderServiceImpl;

public class RetryInterceptor {

    private int maxRetry = 2;

    public void doRetry(String orderId) {
        int i = 0;
        while (i < maxRetry) {
            i++;
            if (orderId == null) {
                continue;
            }
            // 循环链的一环: Interceptor 回调 Service
            OrderServiceImpl.notifyRetry(orderId, i);
        }
    }
}
