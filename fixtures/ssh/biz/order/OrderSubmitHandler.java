package com.legacy.ssh.biz.order;

import com.legacy.ssh.dao.order.OrderDAO;
import com.legacy.ssh.model.order.Order;
import com.legacy.ssh.util.common.LegacyCodeUtil;
import java.util.List;

public class OrderSubmitHandler {

    private OrderDAO orderDAO = new OrderDAO();

    public void beforeSubmit(Order order) {
        if (order == null) {
            throw new IllegalArgumentException("order required");
        }
        LegacyCodeUtil.debug("beforeSubmit:" + order.getOrderId());
    }

    public void afterSubmit(Order order) {
        LegacyCodeUtil.debug("afterSubmit:" + order.getOrderId());
    }

    public void forceCloseByDao(String orderId, String reason) {
        // 越级路径: Biz 直接触达 DAO
        orderDAO.softDelete(orderId);
        LegacyCodeUtil.debug("forceClose:" + reason);
    }

    public void recoverUserOrders(String userId) {
        List<Order> list = orderDAO.listByUser(userId);
        if (list != null && list.size() > 100) {
            LegacyCodeUtil.debug("too many orders");
        }
    }
}
