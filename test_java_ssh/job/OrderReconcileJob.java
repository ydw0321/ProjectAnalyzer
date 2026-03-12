package com.legacy.ssh.job;

import com.legacy.ssh.biz.order.OrderSubmitHandler;
import com.legacy.ssh.service.OrderService;
import com.legacy.ssh.service.impl.order.OrderServiceImpl;
import com.legacy.ssh.util.common.DateUtil;

public class OrderReconcileJob {

    private OrderService orderService = new OrderServiceImpl();
    private OrderSubmitHandler orderSubmitHandler = new OrderSubmitHandler();

    public void run() {
        String batchNo = "JOB-" + DateUtil.nowMillis();
        orderService.reconcile(batchNo);

        // 非标准路径: Job 直接调用 Biz
        orderSubmitHandler.recoverUserOrders("system");
    }

    public void runEmergency() {
        orderService.reconcile("ERR-LEGACY-1");
    }
}
