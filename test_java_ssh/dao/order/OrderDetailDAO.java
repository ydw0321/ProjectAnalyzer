package com.legacy.ssh.dao.order;

import com.legacy.ssh.dao.base.QueryBuilder;
import com.legacy.ssh.model.order.Order;
import com.legacy.ssh.util.common.LegacyCodeUtil;
import java.util.ArrayList;
import java.util.List;

public class OrderDetailDAO {

    private QueryBuilder queryBuilder = new QueryBuilder();

    public List<Order> loadDirtyOrders(String batchNo) {
        String where = queryBuilder.buildOrderWhere(null, "INIT");
        LegacyCodeUtil.debug("loadDirtyOrders:" + where + ":" + batchNo);
        return new ArrayList<Order>();
    }

    public String findItemJson(String orderId) {
        return "{\"order\":\"" + orderId + "\"}";
    }
}
