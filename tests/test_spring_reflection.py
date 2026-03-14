"""Unit tests for Spring/MyBatis reflection rule extraction in JavaParser."""
from _bootstrap import bootstrap_project_root

bootstrap_project_root()

from src.parser.java_parser import JavaParser

parser = JavaParser()


def test_extract_spring_annotations_single_line():
    source = """
public class Svc {
    @Autowired private UserService userService;
    @Autowired private OrderService orderService;
}
"""
    result = parser._extract_spring_annotations(source)
    assert result.get("userService") == "UserService"
    assert result.get("orderService") == "OrderService"


def test_extract_spring_annotations_multiline():
    source = """
public class Svc {
    @Autowired
    private UserService userService;
}
"""
    result = parser._extract_spring_annotations(source)
    assert result.get("userService") == "UserService"


def test_extract_spring_annotations_resource():
    source = """
@Resource(name="payService")
private PayService payService;
"""
    result = parser._extract_spring_annotations(source)
    assert result.get("payService") == "PayService"


def test_extract_spring_annotations_skips_value():
    """@Value fields hold strings, not class types — must be ignored."""
    source = """
@Value("${app.name}")
private String appName;
"""
    result = parser._extract_spring_annotations(source)
    assert "appName" not in result


def test_get_class_annotations_service():
    source = """
@Service
public class UserService {}
"""
    result = parser._get_class_annotations(source)
    assert "Service" in result.get("UserService", [])


def test_get_class_annotations_mapper():
    source = """
@Mapper
public interface UserMapper {}
"""
    result = parser._get_class_annotations(source)
    assert "Mapper" in result.get("UserMapper", [])


def test_get_class_annotations_no_tracked():
    source = """
public class PlainClass {}
"""
    result = parser._get_class_annotations(source)
    assert result == {}


def test_extract_with_calls_spring_fields():
    """Integration: Spring-injected fields appear in callee_class resolution."""
    import tempfile, os
    code = """
import com.example.OrderService;
@Service
public class CheckoutService {
    @Autowired
    private OrderService orderService;
    public void checkout() {
        orderService.createOrder();
    }
}
"""
    with tempfile.NamedTemporaryFile(suffix=".java", mode="w", delete=False, encoding="utf-8") as f:
        f.write(code)
        path = f.name
    try:
        result = parser.extract_with_calls(path)
        ext_calls = result["external_calls"]
        # checkout() calls orderService.createOrder() — should resolve callee_class to OrderService
        matching = [c for c in ext_calls if c["callee"] == "createOrder"]
        assert matching, "Expected createOrder in external_calls"
        assert matching[0]["callee_class"] == "OrderService"
    finally:
        os.unlink(path)
