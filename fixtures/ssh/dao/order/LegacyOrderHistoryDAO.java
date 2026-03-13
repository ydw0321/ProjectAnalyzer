package com.legacy.ssh.dao.order;

import com.legacy.ssh.model.order.Order;
import com.legacy.ssh.util.common.LegacyCodeUtil;
import java.util.ArrayList;
import java.util.List;

public class LegacyOrderHistoryDAO {

    public void save(Order order) {
        LegacyCodeUtil.debug("history save:" + (order == null ? "null" : order.getOrderId()));
    }

    public void update(Order order) {
        LegacyCodeUtil.debug("history update:" + (order == null ? "null" : order.getOrderId()));
    }

    public List<Order> process(String userId) {
        LegacyCodeUtil.debug("history process:" + userId);
        return new ArrayList<Order>();
    }

    public String execute(String sql) {
        return "EXECUTE:" + sql;
    }
}
