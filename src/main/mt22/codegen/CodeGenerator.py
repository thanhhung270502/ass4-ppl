from Emitter import Emitter
from functools import reduce
from Utils import *
from Frame import Frame
from abc import ABC
from Visitor import *
from AST import *

class MType:
    def __init__(self, partype, rettype):
        self.partype = partype
        self.rettype = rettype

class ClassType(Type):
    def __init__(self,cname):
        self.cname = cname
    def __str__(self):
        return "Class({0})".format(str(self.cname))
    def accept(self, v, param):
        return None
    
class Symbol:
    def __init__(self, name, mtype, value=None):
        self.name = name
        self.mtype = mtype
        self.value = value

    def __str__(self):
        return "Symbol(" + self.name + "," + str(self.mtype) + ")"

class CodeGenerator:
    def __init__(self):
        self.libName = "io"

    def init(self):
        return [Symbol("readInteger", MType(list(), IntegerType()), CName(self.libName)),
                Symbol("printInteger", MType([IntegerType()], VoidType()), CName(self.libName)),
                Symbol("readFloat", MType([], FloatType()), CName(self.libName)),
                Symbol("printFloat", MType([FloatType()], VoidType()), CName(self.libName)),
                Symbol("readBoolean", MType([], BooleanType()), CName(self.libName)),
                Symbol("printBoolean", MType([BooleanType()], VoidType()), CName(self.libName)),
                Symbol("readString", MType([], StringType()), CName(self.libName)),
                Symbol("printString", MType([StringType()], VoidType()), CName(self.libName)),
                
                # Will be handle later
                Symbol("super", MType([StringType()], VoidType()), CName(self.libName)),
                Symbol("preventDefault", MType([StringType()], VoidType()), CName(self.libName)),
                ]

    def gen(self, ctx, path):
        # ctx: AST
        # dir_: String

        gl = self.init()
        gc = CodeGenVisitor(ctx, gl, path)
        gc.visit(ctx, None)

class SubBody():
    def __init__(self, frame, sym):
        self.frame = frame
        self.sym = sym

class Access():
    def __init__(self, frame, sym, isLeft, isFirst=False):
        self.frame = frame
        self.sym = sym
        self.isLeft = isLeft
        self.isFirst = isFirst

class Val(ABC):
    pass

class Index(Val):
    def __init__(self, value):
        self.value = value

class CName(Val):
    def __init__(self, value):
        self.value = value

class CodeGenVisitor(Visitor):
    def __init__(self, astTree, env, path):
        self.astTree = astTree
        self.env = env
        self.className = "MT22Class"
        self.path = path
        self.emit = Emitter(self.path + "/" + self.className + ".j")

    def visitProgram(self, ast, c):
        #ast: Program
        #c: Any

        self.emit.printout(self.emit.emitPROLOG(self.className, "java.lang.Object"))
        e = SubBody(None, self.env)
        for x in ast.decls:
            e = self.visit(x, e)
        # generate default constructor
        self.genMETHOD(FuncDecl("<init>", None, list(), None, BlockStmt( list())), c, Frame("<init>", VoidType))
        self.emit.emitEPILOG()
        return c

    def genMETHOD(self, consdecl, o, frame):
        isInit = consdecl.return_type is None
        isMain = consdecl.name == "main" and len(
            consdecl.params) == 0 and type(consdecl.return_type) is VoidType
        returnType = VoidType() if isInit else consdecl.return_type
        methodName = "<init>" if isInit else consdecl.name
        intype = [ArrayType(0, StringType())] if isMain else list(
            map(lambda x: x.typ, consdecl.params))
        mtype = MType(intype, returnType)

        self.emit.printout(self.emit.emitMETHOD(
            methodName, mtype, not isInit, frame))
        frame.enterScope(True)

        glenv = o

        # Generate code for parameter declarations
        if isInit:
            self.emit.printout(self.emit.emitVAR(frame.getNewIndex(), "this", ClassType(
                Id(self.className)), frame.getStartLabel(), frame.getEndLabel(), frame))
        elif isMain:
            self.emit.printout(self.emit.emitVAR(frame.getNewIndex(), "args", ArrayType(
                0, StringType()), frame.getStartLabel(), frame.getEndLabel(), frame))
        else:
            local = reduce(lambda env, ele: SubBody(
                frame, [self.visit(ele, env)]+env.sym), consdecl.param, SubBody(frame, []))
            glenv = local.sym+glenv

        body = consdecl.body
        self.emit.printout(self.emit.emitLABEL(frame.getStartLabel(), frame))

        # Generate code for statements
        if isInit:
            self.emit.printout(self.emit.emitREADVAR(
                "this", ClassType(Id(self.className)), 0, frame))
            self.emit.printout(self.emit.emitINVOKESPECIAL(frame))
        list(map(lambda x: self.visit(x, SubBody(frame, glenv)), body.body))

        self.emit.printout(self.emit.emitLABEL(frame.getEndLabel(), frame))
        if type(returnType) is VoidType:
            self.emit.printout(self.emit.emitRETURN(VoidType(), frame))
        self.emit.printout(self.emit.emitENDMETHOD(frame))
        frame.exitScope()

    def visitFuncDecl(self, ctx, o):
        frame = Frame(ctx.name, ctx.return_type)
        self.genMETHOD(ctx, o, frame)
        return Symbol(ctx.name, MType([x.typ for x in ctx.params], ctx.return_type), CName(self.className))

    def visitParamDecl(self, ctx, o):
        pass
    
    # Expressions
    def visitIntegerType(self, ctx, o): pass
    def visitFloatType(self, ctx, o): pass
    def visitBooleanType(self, ctx, o): pass
    def visitStringType(self, ctx, o): pass
    def visitArrayType(self, ctx, o): pass
    def visitAutoType(self, ctx, o): pass
    def visitVoidType(self, ctx, o): pass

    def visitVarDecl(self, ctx, o): pass
    def visitAssignStmt(self, ctx, o): pass
    def visitBlockStmt(self, ctx, o): pass
    def visitIfStmt(self, ctx, o): pass
    def visitForStmt(self, ctx, o): pass
    def visitWhileStmt(self, ctx, o): pass
    def visitDoWhileStmt(self, ctx, o): pass
    def visitBreakStmt(self, ctx, o): pass
    def visitContinueStmt(self, ctx, o): pass
    def visitReturnStmt(self, ctx, o): pass
    def visitCallStmt(self, ctx, o):
        ctxt = o
        frame = ctxt.frame
        nenv = ctxt.sym
        for s in self.env:
            print(s)
        sym = Utils.lookup(ctx.name, nenv, lambda x: x.name)
        cname = sym.value.value
    
        ctype = sym.mtype

        in_ = ("", list())
        for x in ctx.args:
            str1, typ1 = self.visit(x, Access(frame, nenv, False, True))
            in_ = (in_[0] + str1, in_[1].append(typ1))
        self.emit.printout(in_[0])
        self.emit.printout(self.emit.emitINVOKESTATIC(cname + "/" + ctx.name, ctype, frame))

    # Literals
    def visitIntegerLit(self, ctx, o):
        return self.emit.emitPUSHICONST(ctx.val, o.frame), IntegerType()

    def visitFloatLit(self, ctx, o): 
        return self.emit.emitPUSHFCONST(ctx.value, o.frame), FloatType()
    
    def visitStringLit(self, ctx, o): 
        return self.emit.emitPUSHCONST(ctx.value, StringType(), o.frame), StringType()

    def visitBooleanLit(self, ctx, o): 
        return self.emit.emitPUSHICONST(ctx.value, o.frame), BooleanType()
    
    def visitArrayLit(self, ctx, o): pass

    def visitBinExpr(self, ctx, o):
        e1c, e1t = self.visit(ctx.left, o)
        e2c, e2t = self.visit(ctx.right, o)
        
        code = None
        rtype = None

        if ctx.op in ['+', '-']:
            if e1t is FloatType or e2t is FloatType:
                code = self.emit.emitADDOP(ctx.op, FloatType(), o.frame)
                rtype = FloatType()
            else:
                code = self.emit.emitADDOP(ctx.op, IntegerType(), o.frame)
                rtype = IntegerType()

        elif ctx.op in ['*', '/']:
            if e1t is FloatType or e2t is FloatType:
                code = self.emit.emitMULOP(ctx.op, FloatType(), o.frame)
                rtype = FloatType()
            else:
                code = self.emit.emitMULOP(ctx.op, IntegerType(), o.frame)
            
        elif ctx.op in ['%']:
            code = self.emit.emitMOD(o.frame)
            rtype = IntegerType()
        
        elif ctx.op in ['&&']:
            code = self.emit.emitANDOP(o.frame)
            rtype = BooleanType()

        elif ctx.op in ['||']:
            code = self.emit.emitOROP(o.frame)
            rtype = BooleanType()
        
        # Handle the expression of the string
        elif ctx.op in ['::']:
            pass

        elif ctx.op in ['>','>=','<','<=','!=','==']:
            pass

        # Handle the Implicit Type: Integer -> Float
        if not e1t is rtype:
            e1c += self.emit.emitI2F(o.frame)
        if not e2t is rtype:
            e2c += self.emit.emitI2F(o.frame)
        return e1c + e2c + self.emit.emitADDOP(ctx.op, e1t, o.frame), e1t

    def visitUnExpr(self, ctx, o): pass
    def visitId(self, ctx, o): pass
    def visitArrayCell(self, ctx, o): pass
    def visitFuncCall(self, ctx, o): pass