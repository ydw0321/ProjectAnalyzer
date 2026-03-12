package com.legacy.ssh.util.common;

public class LegacyBeanFactory {

    public static Object newBean(String className) {
        try {
            return Class.forName(className).newInstance();
        } catch (Exception ex) {
            LegacyCodeUtil.debug("newBean fail:" + className);
            return null;
        }
    }

    public static Object getByAlias(String alias) {
        if ("orderDao".equals(alias)) {
            return newBean("com.legacy.ssh.dao.order.OrderDAO");
        }
        if ("orderService".equals(alias)) {
            return newBean("com.legacy.ssh.service.impl.order.OrderServiceImpl");
        }
        return null;
    }
}
