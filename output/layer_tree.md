```mermaid
graph TD
    OrderController[OrderController<br/>(5 methods)]
    subgraph controller
    end
    OrderController -->|BELONGS_TO| controller
    ProductController[ProductController<br/>(3 methods)]
    subgraph controller
    end
    ProductController -->|BELONGS_TO| controller
    UserController[UserController<br/>(3 methods)]
    subgraph controller
    end
    UserController -->|BELONGS_TO| controller
    OrderFacade[OrderFacade<br/>(3 methods)]
    subgraph facade
    end
    OrderFacade -->|BELONGS_TO| facade
    ProductFacade[ProductFacade<br/>(4 methods)]
    subgraph facade
    end
    ProductFacade -->|BELONGS_TO| facade
    UserFacade[UserFacade<br/>(5 methods)]
    subgraph facade
    end
    UserFacade -->|BELONGS_TO| facade
    PaymentService[PaymentService<br/>(9 methods)]
    subgraph service
    end
    PaymentService -->|BELONGS_TO| service
    OrderService[OrderService<br/>(3 methods)]
    subgraph service
    end
    OrderService -->|BELONGS_TO| service
    ProductService[ProductService<br/>(3 methods)]
    subgraph service
    end
    ProductService -->|BELONGS_TO| service
    UserService[UserService<br/>(4 methods)]
    subgraph service
    end
    UserService -->|BELONGS_TO| service
    InventoryService[InventoryService<br/>(5 methods)]
    subgraph service
    end
    InventoryService -->|BELONGS_TO| service
    OrderBiz[OrderBiz<br/>(9 methods)]
    subgraph biz
    end
    OrderBiz -->|BELONGS_TO| biz
    ProductBiz[ProductBiz<br/>(13 methods)]
    subgraph biz
    end
    ProductBiz -->|BELONGS_TO| biz
    UserBiz[UserBiz<br/>(11 methods)]
    subgraph biz
    end
    UserBiz -->|BELONGS_TO| biz
```