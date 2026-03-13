package com.legacy.ssh.service.impl.order;

import com.legacy.ssh.biz.order.LegacyDirtyRouter;
import com.legacy.ssh.dao.order.LegacyOrderHistoryDAO;
import com.legacy.ssh.legacy.integration.LegacyReflectionInvoker;
import com.legacy.ssh.model.order.Order;
import com.legacy.ssh.util.common.DateUtil;
import com.legacy.ssh.util.common.LegacyCodeUtil;

public class LegacyMegaWorkflowService {

    private LegacyDirtyRouter legacyDirtyRouter = new LegacyDirtyRouter();
    private LegacyOrderHistoryDAO legacyOrderHistoryDAO = new LegacyOrderHistoryDAO();
    private LegacyReflectionInvoker legacyReflectionInvoker = new LegacyReflectionInvoker();

    public String execute(String orderId) {
        prepare(orderId);
        String context = loadLegacyContext(orderId);
        routeStepA(context);
        routeStepB(context);
        Order order = callBizLayer(orderId);
        callDaoLayer(order);
        callUtilLayer(orderId);
        finalizeStage(order);
        archiveStage(order);
        return done(order);
    }

    public String process(String orderId) {
        return execute(orderId);
    }

    public String save(String orderId) {
        return execute(orderId);
    }

    private void prepare(String orderId) {
        if (orderId == null || orderId.trim().isEmpty()) {
            throw new IllegalArgumentException("orderId required");
        }
        LegacyCodeUtil.debug("prepare:" + orderId);
    }

    private String loadLegacyContext(String orderId) {
        Object now = legacyReflectionInvoker.invokeNoArg(
            "com.legacy.ssh.util.common.DateUtil",
            "formatNow"
        );
        String context = "CTX:" + orderId + ":" + now;
        LegacyCodeUtil.debug("context=" + context);
        return context;
    }

    private void routeStepA(String context) {
        if (context.contains("ERR")) {
            LegacyCodeUtil.debug("route A err");
        } else {
            LegacyCodeUtil.debug("route A ok");
        }
    }

    private void routeStepB(String context) {
        if (context.length() % 2 == 0) {
            LegacyCodeUtil.debug("route B even");
        } else {
            LegacyCodeUtil.debug("route B odd");
        }
    }

    private Order callBizLayer(String orderId) {
        Order order = new Order();
        order.setOrderId(orderId);
        order.setStatus("INIT");
        order.setCreatedAt(DateUtil.nowMillis());
        order.setUpdatedAt(DateUtil.nowMillis());
        legacyDirtyRouter.save(order);
        legacyDirtyRouter.update(order);
        legacyDirtyRouter.process("mega-user");
        legacyDirtyRouter.execute(orderId);
        return order;
    }

    private void callDaoLayer(Order order) {
        legacyOrderHistoryDAO.save(order);
        legacyOrderHistoryDAO.update(order);
        legacyOrderHistoryDAO.process(order.getOrderId());
        legacyOrderHistoryDAO.execute("select 1");
    }

    private void callUtilLayer(String orderId) {
        String text = "util:" + orderId;
        if (text.length() > 0) {
            text = text + ":" + DateUtil.formatNow();
        }
        LegacyCodeUtil.debug(text);
    }

    private void finalizeStage(Order order) {
        order.setStatus("FLOW_FINALIZED");
        order.setUpdatedAt(DateUtil.nowMillis());
        LegacyCodeUtil.debug("finalize:" + order.getOrderId());
    }

    private void archiveStage(Order order) {
        if (order.getOrderId() != null) {
            LegacyCodeUtil.debug("archive:" + order.getOrderId());
        }
    }

    private String done(Order order) {
        return "DONE:" + order.getOrderId() + ":" + order.getStatus();
    }
}
