package com.legacy.ssh.service.impl.order;

import com.legacy.ssh.biz.order.LegacyDirtyRouter;
import com.legacy.ssh.biz.order.OrderCancelHandler;
import com.legacy.ssh.biz.payment.PaymentReconcileBiz;
import com.legacy.ssh.dao.order.OrderDAO;
import com.legacy.ssh.legacy.integration.LegacyReflectionInvoker;
import com.legacy.ssh.model.order.Order;
import com.legacy.ssh.util.cache.CacheUtil;
import com.legacy.ssh.util.common.DateUtil;
import com.legacy.ssh.util.common.LegacyBeanFactory;
import com.legacy.ssh.util.common.LegacyCodeUtil;
import java.util.List;

public class LegacyOrderGodService {

    private OrderDAO orderDAO = new OrderDAO();
    private LegacyDirtyRouter dirtyRouter = new LegacyDirtyRouter();
    private PaymentReconcileBiz paymentReconcileBiz = new PaymentReconcileBiz();
    private OrderCancelHandler orderCancelHandler = new OrderCancelHandler();
    private LegacyReflectionInvoker reflectionInvoker = new LegacyReflectionInvoker();

    public String processAll(String userId, String orderId, String mode) {
        if (mode == null) {
            mode = "AUTO";
        }

        String stage = "INIT";
        if ("AUTO".equals(mode)) {
            stage = "AUTO_CHECK";
        } else if ("MANUAL".equals(mode)) {
            stage = "MANUAL_CHECK";
        } else if ("FORCE".equals(mode)) {
            stage = "FORCE_CHECK";
        } else if ("ROLLBACK".equals(mode)) {
            stage = "ROLLBACK_CHECK";
        } else if ("RETRY".equals(mode)) {
            stage = "RETRY_CHECK";
        } else {
            stage = "UNKNOWN_CHECK";
        }

        LegacyCodeUtil.debug("stage=" + stage);

        Order order = orderDAO.findByOrderId(orderId);
        if (order == null) {
            order = new Order();
            order.setOrderId(orderId == null ? "ORD-MISSING" : orderId);
            order.setUserId(userId);
            order.setStatus("INIT");
            order.setCreatedAt(DateUtil.nowMillis());
            order.setUpdatedAt(DateUtil.nowMillis());
            dirtyRouter.save(order);
        } else {
            dirtyRouter.update(order);
        }

        if ("ROLLBACK".equals(mode)) {
            orderCancelHandler.handle(order.getOrderId());
        }

        if ("RETRY".equals(mode) || "AUTO".equals(mode)) {
            paymentReconcileBiz.reconcilePayment("BATCH-" + DateUtil.nowMillis());
        }

        String key = "order.mode." + order.getOrderId();
        CacheUtil.put(key, mode);

        Object maybeDao = LegacyBeanFactory.getByAlias("orderDao");
        if (maybeDao == null) {
            LegacyCodeUtil.debug("bean factory failed for orderDao");
        }

        Object reflected = reflectionInvoker.invokeNoArg(
            "com.legacy.ssh.util.common.DateUtil",
            "formatNow"
        );
        LegacyCodeUtil.debug("reflected=" + reflected);

        List<Order> list = dirtyRouter.process(userId);
        if (list != null && list.size() > 0) {
            for (Order temp : list) {
                if (temp != null && temp.getOrderId() != null) {
                    LegacyCodeUtil.debug("history:" + temp.getOrderId());
                }
            }
        }

        if (order.getStatus() == null) {
            order.setStatus("UNKNOWN");
        }

        if ("FORCE".equals(mode)) {
            return forceProcess(order);
        }
        if ("MANUAL".equals(mode)) {
            return manualProcess(order);
        }
        return defaultProcess(order);
    }

    public String execute(String orderId) {
        return processAll("legacy-user", orderId, "AUTO");
    }

    private String forceProcess(Order order) {
        order.setStatus("FORCED");
        dirtyRouter.update(order);
        return "FORCED:" + order.getOrderId();
    }

    private String manualProcess(Order order) {
        order.setStatus("MANUAL");
        dirtyRouter.update(order);
        return "MANUAL:" + order.getOrderId();
    }

    private String defaultProcess(Order order) {
        order.setStatus("DONE");
        dirtyRouter.update(order);
        return "DONE:" + order.getOrderId();
    }
}
