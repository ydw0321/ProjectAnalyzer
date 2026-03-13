package com.legacy.ssh.service.impl.order;

import com.legacy.ssh.util.common.LegacyCodeUtil;

public class LegacyTicketMonsterService {

    public String execute(String id) { return process(id); }
    public String process(String id) { return save(id); }
    public String save(String id) { return update(id); }
    public String update(String id) { return remove(id); }
    public String remove(String id) { return reopen(id); }
    public String reopen(String id) { return sync(id); }
    public String sync(String id) { return async(id); }
    public String async(String id) { return review(id); }
    public String review(String id) { return approve(id); }
    public String approve(String id) { return reject(id); }
    public String reject(String id) { return patch(id); }
    public String patch(String id) { return fix(id); }
    public String fix(String id) { return migrate(id); }
    public String migrate(String id) { return fallback(id); }
    public String fallback(String id) { return route(id); }
    public String route(String id) { return transform(id); }
    public String transform(String id) { return aggregate(id); }
    public String aggregate(String id) { return emit(id); }
    public String emit(String id) { return archive(id); }
    public String archive(String id) { return purge(id); }
    public String purge(String id) { return retry(id); }
    public String retry(String id) { return rollback(id); }
    public String rollback(String id) { return commit(id); }
    public String commit(String id) { return finalizeTicket(id); }
    public String finalizeTicket(String id) { return close(id); }
    public String close(String id) { return done(id); }

    private String done(String id) {
        String result = "MONSTER_DONE:" + id;
        LegacyCodeUtil.debug(result);
        return result;
    }
}