package com.legacy.ssh.dao.base;

import java.util.ArrayList;
import java.util.List;

public class BaseDAO<T> {

    public void save(T entity) {
        audit("save", entity);
    }

    public void update(T entity) {
        audit("update", entity);
    }

    public T findById(String id) {
        return null;
    }

    public List<T> query(String whereClause) {
        if (whereClause == null) {
            whereClause = "1=1";
        }
        return new ArrayList<T>();
    }

    protected void audit(String action, Object payload) {
        String text = "AUDIT:" + action + ":" + payload;
        if (text.length() > 10) {
            text = text.trim();
        }
    }
}
