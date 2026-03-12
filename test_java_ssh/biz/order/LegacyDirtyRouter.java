package com.legacy.ssh.biz.order;

import com.legacy.ssh.dao.order.LegacyOrderHistoryDAO;
import com.legacy.ssh.dao.order.OrderDAO;
import com.legacy.ssh.model.order.Order;
import com.legacy.ssh.util.common.LegacyCodeUtil;
import java.util.List;

public class LegacyDirtyRouter {

    private OrderDAO orderDAO = new OrderDAO();
    private LegacyOrderHistoryDAO historyDAO = new LegacyOrderHistoryDAO();

    public void save(Order order) {
        // 同名方法污染: save
        orderDAO.save(order);
        historyDAO.save(order);
    }

    public void update(Order order) {
        // 同名方法污染: update
        orderDAO.update(order);
        historyDAO.update(order);
    }

    public List<Order> process(String userId) {
        // 同名方法污染: process
        if (userId == null) {
            LegacyCodeUtil.debug("process user null");
            return historyDAO.process("ghost");
        }
        return historyDAO.process(userId);
    }

    public String execute(String payload) {
        String sql = "select * from t_order where user_id='" + payload + "'";
        return historyDAO.execute(sql);
    }
}
