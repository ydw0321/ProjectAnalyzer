```mermaid
graph TD
    UserController[UserController<br/>(5 methods)]
    subgraph controller
    end
    UserController -->|BELONGS_TO| controller
    ProductController[ProductController<br/>(6 methods)]
    subgraph controller
    end
    ProductController -->|BELONGS_TO| controller
    OrderController[OrderController<br/>(5 methods)]
    subgraph controller
    end
    OrderController -->|BELONGS_TO| controller
    ProductFacade[ProductFacade<br/>(5 methods)]
    subgraph facade
    end
    ProductFacade -->|BELONGS_TO| facade
    UserFacade[UserFacade<br/>(5 methods)]
    subgraph facade
    end
    UserFacade -->|BELONGS_TO| facade
    OrderFacade[OrderFacade<br/>(3 methods)]
    subgraph facade
    end
    OrderFacade -->|BELONGS_TO| facade
    UserService[UserService<br/>(6 methods)]
    subgraph service
    end
    UserService -->|BELONGS_TO| service
    ProductService[ProductService<br/>(6 methods)]
    subgraph service
    end
    ProductService -->|BELONGS_TO| service
    InventoryService[InventoryService<br/>(5 methods)]
    subgraph service
    end
    InventoryService -->|BELONGS_TO| service
    OrderService[OrderService<br/>(5 methods)]
    subgraph service
    end
    OrderService -->|BELONGS_TO| service
    PaymentService[PaymentService<br/>(8 methods)]
    subgraph service
    end
    PaymentService -->|BELONGS_TO| service
    WechatPaymentServiceImpl[WechatPaymentServiceImpl<br/>(3 methods)]
    subgraph service
    end
    WechatPaymentServiceImpl -->|BELONGS_TO| service
    LegacyPaymentServiceImpl[LegacyPaymentServiceImpl<br/>(3 methods)]
    subgraph service
    end
    LegacyPaymentServiceImpl -->|BELONGS_TO| service
    AlipayPaymentServiceImpl[AlipayPaymentServiceImpl<br/>(3 methods)]
    subgraph service
    end
    AlipayPaymentServiceImpl -->|BELONGS_TO| service
    OrderServiceImpl[OrderServiceImpl<br/>(11 methods)]
    subgraph service
    end
    OrderServiceImpl -->|BELONGS_TO| service
    OrderServiceProxy[OrderServiceProxy<br/>(4 methods)]
    subgraph service
    end
    OrderServiceProxy -->|BELONGS_TO| service
    OrderServiceAsync[OrderServiceAsync<br/>(4 methods)]
    subgraph service
    end
    OrderServiceAsync -->|BELONGS_TO| service
    LegacyOrderGodService[LegacyOrderGodService<br/>(5 methods)]
    subgraph service
    end
    LegacyOrderGodService -->|BELONGS_TO| service
    LegacyMegaWorkflowService[LegacyMegaWorkflowService<br/>(13 methods)]
    subgraph service
    end
    LegacyMegaWorkflowService -->|BELONGS_TO| service
    DeepNode2PaymentService[DeepNode2PaymentService<br/>(1 methods)]
    subgraph service
    end
    DeepNode2PaymentService -->|BELONGS_TO| service
    LegacyTicketMonsterService[LegacyTicketMonsterService<br/>(27 methods)]
    subgraph service
    end
    LegacyTicketMonsterService -->|BELONGS_TO| service
    DeepChainCoordinator[DeepChainCoordinator<br/>(1 methods)]
    subgraph service
    end
    DeepChainCoordinator -->|BELONGS_TO| service
    DeepNode11FinalService[DeepNode11FinalService<br/>(1 methods)]
    subgraph service
    end
    DeepNode11FinalService -->|BELONGS_TO| service
    OrderBiz[OrderBiz<br/>(9 methods)]
    subgraph biz
    end
    OrderBiz -->|BELONGS_TO| biz
    UserBiz[UserBiz<br/>(11 methods)]
    subgraph biz
    end
    UserBiz -->|BELONGS_TO| biz
    ProductBiz[ProductBiz<br/>(13 methods)]
    subgraph biz
    end
    ProductBiz -->|BELONGS_TO| biz
    PaymentReconcileBiz[PaymentReconcileBiz<br/>(1 methods)]
    subgraph biz
    end
    PaymentReconcileBiz -->|BELONGS_TO| biz
    PaymentGatewayBiz[PaymentGatewayBiz<br/>(2 methods)]
    subgraph biz
    end
    PaymentGatewayBiz -->|BELONGS_TO| biz
    LegacyOrderAuditBiz[LegacyOrderAuditBiz<br/>(2 methods)]
    subgraph biz
    end
    LegacyOrderAuditBiz -->|BELONGS_TO| biz
    OrderCancelHandler[OrderCancelHandler<br/>(1 methods)]
    subgraph biz
    end
    OrderCancelHandler -->|BELONGS_TO| biz
    OrderSubmitHandler[OrderSubmitHandler<br/>(4 methods)]
    subgraph biz
    end
    OrderSubmitHandler -->|BELONGS_TO| biz
    LegacyDirtyRouter[LegacyDirtyRouter<br/>(4 methods)]
    subgraph biz
    end
    LegacyDirtyRouter -->|BELONGS_TO| biz
    LegacyExecutePaymentBiz[LegacyExecutePaymentBiz<br/>(3 methods)]
    subgraph biz
    end
    LegacyExecutePaymentBiz -->|BELONGS_TO| biz
    DeepNode8PaymentBiz[DeepNode8PaymentBiz<br/>(1 methods)]
    subgraph biz
    end
    DeepNode8PaymentBiz -->|BELONGS_TO| biz
    DeepNode1Biz[DeepNode1Biz<br/>(1 methods)]
    subgraph biz
    end
    DeepNode1Biz -->|BELONGS_TO| biz
    OrderDal[OrderDal<br/>(5 methods)]
    subgraph dal
    end
    OrderDal -->|BELONGS_TO| dal
    UserDal[UserDal<br/>(5 methods)]
    subgraph dal
    end
    UserDal -->|BELONGS_TO| dal
    ProductDal[ProductDal<br/>(4 methods)]
    subgraph dal
    end
    ProductDal -->|BELONGS_TO| dal
    OrderDetailDAO[OrderDetailDAO<br/>(2 methods)]
    subgraph dao
    end
    OrderDetailDAO -->|BELONGS_TO| dao
    OrderDAO[OrderDAO<br/>(4 methods)]
    subgraph dao
    end
    OrderDAO -->|BELONGS_TO| dao
    OrderStatisticsDAO[OrderStatisticsDAO<br/>(2 methods)]
    subgraph dao
    end
    OrderStatisticsDAO -->|BELONGS_TO| dao
    QueryBuilder[QueryBuilder<br/>(2 methods)]
    subgraph dao
    end
    QueryBuilder -->|BELONGS_TO| dao
    BaseDAO[BaseDAO<br/>(5 methods)]
    subgraph dao
    end
    BaseDAO -->|BELONGS_TO| dao
    LegacyOrderHistoryDAO[LegacyOrderHistoryDAO<br/>(4 methods)]
    subgraph dao
    end
    LegacyOrderHistoryDAO -->|BELONGS_TO| dao
    LegacyExecuteOrderDAO[LegacyExecuteOrderDAO<br/>(3 methods)]
    subgraph dao
    end
    LegacyExecuteOrderDAO -->|BELONGS_TO| dao
    DeepNode3OrderDAO[DeepNode3OrderDAO<br/>(1 methods)]
    subgraph dao
    end
    DeepNode3OrderDAO -->|BELONGS_TO| dao
    DeepNode9BaseDAO[DeepNode9BaseDAO<br/>(1 methods)]
    subgraph dao
    end
    DeepNode9BaseDAO -->|BELONGS_TO| dao
    Product[Product<br/>(10 methods)]
    subgraph model
    end
    Product -->|BELONGS_TO| model
    Order[Order<br/>(20 methods)]
    subgraph model
    end
    Order -->|BELONGS_TO| model
    User[User<br/>(14 methods)]
    subgraph model
    end
    User -->|BELONGS_TO| model
    User[User<br/>(14 methods)]
    subgraph model
    end
    User -->|BELONGS_TO| model
    OrderItem[OrderItem<br/>(6 methods)]
    subgraph model
    end
    OrderItem -->|BELONGS_TO| model
    Order[Order<br/>(20 methods)]
    subgraph model
    end
    Order -->|BELONGS_TO| model
    IdGenerator[IdGenerator<br/>(4 methods)]
    subgraph util
    end
    IdGenerator -->|BELONGS_TO| util
    PriceCalculator[PriceCalculator<br/>(3 methods)]
    subgraph util
    end
    PriceCalculator -->|BELONGS_TO| util
    DateUtil[DateUtil<br/>(6 methods)]
    subgraph util
    end
    DateUtil -->|BELONGS_TO| util
    LocalCache[LocalCache<br/>(3 methods)]
    subgraph util
    end
    LocalCache -->|BELONGS_TO| util
    CacheUtil[CacheUtil<br/>(3 methods)]
    subgraph util
    end
    CacheUtil -->|BELONGS_TO| util
    LegacyCodeUtil[LegacyCodeUtil<br/>(2 methods)]
    subgraph util
    end
    LegacyCodeUtil -->|BELONGS_TO| util
    SqlBuilderUtil[SqlBuilderUtil<br/>(2 methods)]
    subgraph util
    end
    SqlBuilderUtil -->|BELONGS_TO| util
    DateUtil[DateUtil<br/>(6 methods)]
    subgraph util
    end
    DateUtil -->|BELONGS_TO| util
    StringMaskUtil[StringMaskUtil<br/>(2 methods)]
    subgraph util
    end
    StringMaskUtil -->|BELONGS_TO| util
    LegacyBeanFactory[LegacyBeanFactory<br/>(2 methods)]
    subgraph util
    end
    LegacyBeanFactory -->|BELONGS_TO| util
    LegacyExecuteHelper[LegacyExecuteHelper<br/>(3 methods)]
    subgraph util
    end
    LegacyExecuteHelper -->|BELONGS_TO| util
    DeepNode10CacheUtil[DeepNode10CacheUtil<br/>(1 methods)]
    subgraph util
    end
    DeepNode10CacheUtil -->|BELONGS_TO| util
    DeepNode4Util[DeepNode4Util<br/>(1 methods)]
    subgraph util
    end
    DeepNode4Util -->|BELONGS_TO| util
```