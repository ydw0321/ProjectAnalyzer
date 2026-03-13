package com.legacy.ssh.service;

import com.legacy.ssh.model.order.Order;

public interface PaymentService {

    String pay(Order order);

    boolean reverse(Order order);

    String getChannelCode();
}
