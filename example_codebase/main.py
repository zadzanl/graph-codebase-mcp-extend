from models import Employee
from utils import MathOps, make_multiplier
from events import EventBus

def on_task_assigned(data):
    print(f"Event received: Task assigned to {data}")

if __name__ == "__main__":
    # 物件建立與方法呼叫
    alice = Employee("Alice", "Engineer")
    print(alice.greet())
    alice.work()

    # 呼叫 Static 與 Class Methods
    print(MathOps.add(3, 4))
    print(MathOps.scale(5))

    # 使用 Closure
    times3 = make_multiplier(3)
    print(times3(10))

    # 事件驅動示例
    bus = EventBus()
    bus.subscribe("task_assigned", on_task_assigned)
    bus.publish("task_assigned", alice.name) 