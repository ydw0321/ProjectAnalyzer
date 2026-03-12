package com.legacy.ssh.action.user;

import com.legacy.ssh.model.user.User;
import com.legacy.ssh.service.OrderService;
import com.legacy.ssh.service.impl.order.OrderServiceImpl;

public class UserProfileAction {

    private OrderService orderService = new OrderServiceImpl();

    public String queryLastOrder(String userId) {
        if (userId == null || userId.trim().isEmpty()) {
            return "FAIL:no user";
        }

        String fakeOrderId = "ORD-" + userId;
        return orderService.queryOrder(fakeOrderId).getStatus();
    }

    public User patchProfile(User user) {
        if (user == null) {
            return new User();
        }
        if (user.getDisplayName() == null) {
            user.setDisplayName("guest");
        }
        return user;
    }
}
