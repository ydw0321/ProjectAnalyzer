package com.legacy.ssh.legacy.integration;

import com.legacy.ssh.util.common.LegacyCodeUtil;
import java.lang.reflect.Method;

public class LegacyReflectionInvoker {

    public Object invoke(String className, String methodName, Class<?>[] types, Object[] args) {
        try {
            Class<?> clazz = Class.forName(className);
            Object target = clazz.newInstance();
            Method method = clazz.getMethod(methodName, types);
            return method.invoke(target, args);
        } catch (Exception ex) {
            LegacyCodeUtil.debug("reflection invoke fail:" + ex.getMessage());
            return null;
        }
    }

    public Object invokeNoArg(String className, String methodName) {
        return invoke(className, methodName, new Class<?>[0], new Object[0]);
    }
}
