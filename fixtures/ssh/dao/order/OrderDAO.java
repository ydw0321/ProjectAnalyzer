package com.legacy.ssh.dao.order;

import com.legacy.ssh.dao.base.BaseDAO;
import com.legacy.ssh.model.order.Order;
import com.legacy.ssh.util.common.LegacyCodeUtil;
import java.util.List;

public class OrderDAO extends BaseDAO<Order> {

    public Order findByOrderId(String orderId) {
        LegacyCodeUtil.debug("findByOrderId:" + orderId);
        return findById(orderId);
    }

    public void softDelete(String orderId) {
        LegacyCodeUtil.debug("softDelete:" + orderId);
    }

    public List<Order> listByUser(String userId) {
        String where = "user_id='" + userId + "' and flag!='D'";
        return query(where);
    }

    public void markStatus(String orderId, String status) {
        LegacyCodeUtil.debug("markStatus:" + orderId + ":" + status);
    }
}
