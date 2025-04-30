import ast
import os
from typing import Dict, List, Optional, Tuple, Any, Union
import json


class CodeNode:
    """代表程式碼中的節點（類別、函數、變數等）"""

    def __init__(
        self,
        node_id: str,
        node_type: str,
        name: str,
        file_path: str,
        line_no: int,
        end_line_no: Optional[int] = None,
        properties: Dict[str, Any] = None,
    ):
        self.node_id = node_id
        self.node_type = node_type
        self.name = name
        self.file_path = file_path
        self.line_no = line_no
        self.end_line_no = end_line_no
        self.properties = properties or {}
        self.code_snippet = ""

    def __str__(self):
        return f"{self.node_type}:{self.name} ({self.file_path}:{self.line_no})"


class CodeRelation:
    """代表程式碼中的關係（調用、繼承等）"""

    def __init__(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        properties: Dict[str, Any] = None,
    ):
        self.source_id = source_id
        self.target_id = target_id
        self.relation_type = relation_type
        self.properties = properties or {}

    def __str__(self):
        return f"{self.source_id} -{self.relation_type}-> {self.target_id}"


class ASTParser:
    """使用 Python AST 模組解析程式碼的解析器"""

    def __init__(self):
        self.nodes: Dict[str, CodeNode] = {}
        self.relations: List[CodeRelation] = []
        self.current_file: str = ""
        self.current_function: Optional[str] = None
        self.current_class: Optional[str] = None
        self.imports: Dict[str, str] = {}

    def parse_file(self, file_path: str) -> Tuple[Dict[str, CodeNode], List[CodeRelation]]:
        """解析單個Python檔案"""
        print(f"解析檔案: {file_path}")
        self.current_file = file_path
        self.imports = {}

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                file_content = file.read()
                tree = ast.parse(file_content)
                self._create_file_node(file_path)
                self._parse_ast(tree)

            return self.nodes, self.relations
        except Exception as e:
            print(f"解析檔案 {file_path} 時發生錯誤: {e}")
            return {}, []

    def parse_directory(self, directory_path: str) -> Tuple[Dict[str, CodeNode], List[CodeRelation]]:
        """解析目錄中的所有Python檔案"""
        self.nodes = {}
        self.relations = []

        for root, _, files in os.walk(directory_path):
            for file_name in files:
                if file_name.endswith(".py"):
                    file_path = os.path.join(root, file_name)
                    self.parse_file(file_path)

        return self.nodes, self.relations

    def _create_file_node(self, file_path: str) -> str:
        """創建檔案節點"""
        file_name = os.path.basename(file_path)
        node_id = f"file:{file_path}"
        self.nodes[node_id] = CodeNode(
            node_id=node_id,
            node_type="File",
            name=file_name,
            file_path=file_path,
            line_no=0,
        )
        return node_id

    def _get_node_id(self, node_type: str, name: str, file_path: str, line_no: int) -> str:
        """生成節點唯一標識符"""
        return f"{node_type}:{file_path}:{name}:{line_no}"

    def _parse_ast(self, tree: ast.AST) -> None:
        """遞迴解析AST樹狀結構"""
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                self._parse_class(node)
            elif isinstance(node, ast.FunctionDef):
                self._parse_function(node)
            elif isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                self._parse_import(node)
            elif isinstance(node, ast.Assign):
                self._parse_assignment(node)
            else:
                self._parse_ast(node)

    def _parse_class(self, node: ast.ClassDef) -> None:
        """解析類別定義"""
        prev_class = self.current_class
        node_id = self._get_node_id("Class", node.name, self.current_file, node.lineno)
        
        # 創建類別節點
        self.nodes[node_id] = CodeNode(
            node_id=node_id,
            node_type="Class",
            name=node.name,
            file_path=self.current_file,
            line_no=node.lineno,
            end_line_no=getattr(node, "end_lineno", None),
        )
        
        # 創建檔案包含類別的關係
        file_node_id = f"file:{self.current_file}"
        self.relations.append(
            CodeRelation(
                source_id=file_node_id,
                target_id=node_id,
                relation_type="CONTAINS",
            )
        )
        
        # 處理類別繼承
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_name = base.id
                if base_name in self.imports:
                    base_name = self.imports[base_name]
                
                # 創建繼承關係
                self.relations.append(
                    CodeRelation(
                        source_id=node_id,
                        target_id=f"Class:{self.current_file}:{base_name}:0",  # 假設的目標ID
                        relation_type="EXTENDS",
                    )
                )
        
        # 設置當前類別上下文
        self.current_class = node_id
        
        # 解析類別內部成員
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                self._parse_method(item)
            elif isinstance(item, ast.Assign):
                self._parse_class_attribute(item)
        
        # 恢復上下文
        self.current_class = prev_class

    def _parse_method(self, node: ast.FunctionDef) -> None:
        """解析類別方法"""
        node_id = self._get_node_id("Method", node.name, self.current_file, node.lineno)
        
        # 創建方法節點
        self.nodes[node_id] = CodeNode(
            node_id=node_id,
            node_type="Method",
            name=node.name,
            file_path=self.current_file,
            line_no=node.lineno,
            end_line_no=getattr(node, "end_lineno", None),
            properties={"is_method": True},
        )
        
        # 創建類別定義方法的關係
        self.relations.append(
            CodeRelation(
                source_id=self.current_class,
                target_id=node_id,
                relation_type="DEFINES",
            )
        )
        
        # 設置當前函數上下文並解析函數體
        prev_function = self.current_function
        self.current_function = node_id
        
        # 解析函數參數
        self._parse_function_args(node, node_id)
        
        # 解析函數體
        for item in node.body:
            if isinstance(item, ast.Expr):
                if isinstance(item.value, ast.Str):
                    # 處理函數文檔字串
                    self.nodes[node_id].properties["docstring"] = item.value.s
            
            # 尋找函數調用
            self._find_function_calls(item)
        
        # 恢復上下文
        self.current_function = prev_function

    def _parse_function(self, node: ast.FunctionDef) -> None:
        """解析函數定義"""
        node_id = self._get_node_id("Function", node.name, self.current_file, node.lineno)
        
        # 創建函數節點
        self.nodes[node_id] = CodeNode(
            node_id=node_id,
            node_type="Function",
            name=node.name,
            file_path=self.current_file,
            line_no=node.lineno,
            end_line_no=getattr(node, "end_lineno", None),
            properties={"is_method": False},
        )
        
        # 創建檔案包含函數的關係
        file_node_id = f"file:{self.current_file}"
        self.relations.append(
            CodeRelation(
                source_id=file_node_id,
                target_id=node_id,
                relation_type="CONTAINS",
            )
        )
        
        # 設置當前函數上下文
        prev_function = self.current_function
        self.current_function = node_id
        
        # 解析函數參數
        self._parse_function_args(node, node_id)
        
        # 解析函數體
        for item in node.body:
            if isinstance(item, ast.Expr):
                if isinstance(item.value, ast.Str):
                    # 處理函數文檔字串
                    self.nodes[node_id].properties["docstring"] = item.value.s
            
            # 尋找函數調用
            self._find_function_calls(item)
        
        # 恢復上下文
        self.current_function = prev_function

    def _parse_function_args(self, node: ast.FunctionDef, node_id: str) -> None:
        """解析函數參數"""
        args = []
        
        # 處理位置參數
        for arg in node.args.args:
            arg_info = {"name": arg.arg}
            if arg.annotation:
                if isinstance(arg.annotation, ast.Name):
                    arg_info["type"] = arg.annotation.id
            args.append(arg_info)
        
        # 處理預設參數
        defaults = node.args.defaults
        if defaults:
            offset = len(args) - len(defaults)
            for i, default in enumerate(defaults):
                index = offset + i
                if index < len(args):
                    args[index]["has_default"] = True
        
        # 將參數列表序列化為JSON字符串，而不是直接存儲字典
        self.nodes[node_id].properties["args"] = json.dumps(args)

    def _parse_import(self, node: Union[ast.Import, ast.ImportFrom]) -> None:
        """解析導入語句"""
        file_node_id = f"file:{self.current_file}"
        
        if isinstance(node, ast.Import):
            for name in node.names:
                import_name = name.name
                asname = name.asname or import_name
                
                # 添加到導入映射
                self.imports[asname] = import_name
                
                # 創建導入關係
                self.relations.append(
                    CodeRelation(
                        source_id=file_node_id,
                        target_id=f"Module:{import_name}",  # 模組的ID格式
                        relation_type="IMPORTS",
                        properties={"alias": asname if asname != import_name else None},
                    )
                )
        
        elif isinstance(node, ast.ImportFrom):
            module_name = node.module
            for name in node.names:
                import_name = name.name
                asname = name.asname or import_name
                
                # 添加到導入映射
                if module_name:
                    full_name = f"{module_name}.{import_name}"
                    self.imports[asname] = full_name
                else:
                    self.imports[asname] = import_name
                
                # 創建導入關係
                self.relations.append(
                    CodeRelation(
                        source_id=file_node_id,
                        target_id=f"Module:{module_name}.{import_name}" if module_name else f"Module:{import_name}",
                        relation_type="IMPORTS",
                        properties={
                            "alias": asname if asname != import_name else None,
                            "level": node.level,  # 相對導入的層級
                        },
                    )
                )

    def _parse_assignment(self, node: ast.Assign) -> None:
        """解析賦值語句"""
        for target in node.targets:
            if isinstance(target, ast.Name):
                var_name = target.id
                node_id = self._get_node_id("Variable", var_name, self.current_file, node.lineno)
                
                if self.current_class and not self.current_function:
                    # 類別屬性
                    self.nodes[node_id] = CodeNode(
                        node_id=node_id,
                        node_type="ClassVariable",
                        name=var_name,
                        file_path=self.current_file,
                        line_no=node.lineno,
                        end_line_no=getattr(node, "end_lineno", None),
                    )
                    
                    self.relations.append(
                        CodeRelation(
                            source_id=self.current_class,
                            target_id=node_id,
                            relation_type="DEFINES",
                        )
                    )
                elif self.current_function:
                    # 局部變數
                    self.nodes[node_id] = CodeNode(
                        node_id=node_id,
                        node_type="LocalVariable",
                        name=var_name,
                        file_path=self.current_file,
                        line_no=node.lineno,
                        end_line_no=getattr(node, "end_lineno", None),
                    )
                    
                    self.relations.append(
                        CodeRelation(
                            source_id=self.current_function,
                            target_id=node_id,
                            relation_type="DEFINES",
                        )
                    )
                else:
                    # 全局變數
                    self.nodes[node_id] = CodeNode(
                        node_id=node_id,
                        node_type="GlobalVariable",
                        name=var_name,
                        file_path=self.current_file,
                        line_no=node.lineno,
                        end_line_no=getattr(node, "end_lineno", None),
                    )
                    
                    file_node_id = f"file:{self.current_file}"
                    self.relations.append(
                        CodeRelation(
                            source_id=file_node_id,
                            target_id=node_id,
                            relation_type="DEFINES",
                        )
                    )

    def _parse_class_attribute(self, node: ast.Assign) -> None:
        """解析類別屬性"""
        # 與 _parse_assignment 類似，但專門處理類別內部的屬性
        for target in node.targets:
            if isinstance(target, ast.Name):
                var_name = target.id
                node_id = self._get_node_id("ClassVariable", var_name, self.current_file, node.lineno)
                
                self.nodes[node_id] = CodeNode(
                    node_id=node_id,
                    node_type="ClassVariable",
                    name=var_name,
                    file_path=self.current_file,
                    line_no=node.lineno,
                    end_line_no=getattr(node, "end_lineno", None),
                )
                
                self.relations.append(
                    CodeRelation(
                        source_id=self.current_class,
                        target_id=node_id,
                        relation_type="DEFINES",
                    )
                )

    def _find_function_calls(self, node: ast.AST) -> None:
        """在AST節點中尋找函數調用"""
        if isinstance(node, ast.Call):
            func = node.func
            
            if isinstance(func, ast.Name):
                # 直接函數調用
                func_name = func.id
                if self.current_function:
                    self.relations.append(
                        CodeRelation(
                            source_id=self.current_function,
                            target_id=f"Function:{self.current_file}:{func_name}:0",  # 假設的目標ID
                            relation_type="CALLS",
                        )
                    )
            
            elif isinstance(func, ast.Attribute):
                # 調用物件的方法
                if isinstance(func.value, ast.Name):
                    obj_name = func.value.id
                    method_name = func.attr
                    
                    if self.current_function:
                        # 這裡創建對象.方法的調用關係
                        self.relations.append(
                            CodeRelation(
                                source_id=self.current_function,
                                target_id=f"Method:{self.current_file}:{method_name}:0",  # 假設的目標ID
                                relation_type="CALLS",
                                properties={"object": obj_name},
                            )
                        )
        
        # 遞迴查找嵌套的函數調用
        for child in ast.iter_child_nodes(node):
            self._find_function_calls(child)


# 使用範例
if __name__ == "__main__":
    parser = ASTParser()
    nodes, relations = parser.parse_file("example.py")
    
    print("找到的節點:")
    for node in nodes.values():
        print(f"  {node}")
    
    print("\n找到的關係:")
    for relation in relations:
        print(f"  {relation}") 