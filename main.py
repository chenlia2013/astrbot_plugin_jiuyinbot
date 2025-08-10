from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

from astrbot.core.config.astrbot_config import AstrBotConfig
from astrbot.core import html_renderer
from astrbot.core.star.register import register_llm_tool as llm_tool

# star register
from astrbot.core.star.register import (
    register_command as command,
    register_command_group as command_group,
    register_event_message_type as event_message_type,
    register_regex as regex,
    register_platform_adapter_type as platform_adapter_type,
)
from astrbot.core.star.filter.event_message_type import (
    EventMessageTypeFilter,
    EventMessageType,
)

from astrbot.core.star.register import (
    register_star as register,  # 注册插件（Star）
)
from astrbot.core.star import Context, Star
from astrbot.core.star.config import *

import paho.mqtt.client as mqtt

from astrbot.core.message.message_event_result import (
    MessageEventResult,
    MessageChain,
    CommandResult,
    EventResultType,
    ResultContentType,
)

import asyncio 
import json

@register("算卦", "TargetName", "一个简单的 Hello World 插件", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.mqtt_client = mqtt.Client(userdata=context)
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_topic = [("this is astrbot", 2), ("game/player/info_update", 0)] 
        if self.config.get("mqtt_user"):
            self.mqtt_client.username_pw_set(self.config.get("mqtt_user"), self.config.get("mqtt_pwd"))
        self.mqtt_client.connect(self.config.get("mqtt_ip"), self.config.get("mqtt_port"), 60)
        self.mqtt_client.loop_start()
        logger.info(self.config)
        # 异步启动任务检查器
        self.task_running = True
        self.target_map = {}   # 格式: {umo: set(target1, target2, ...)}
        self.msgs = {}  # 格式: 
        self.scene_map = {
            "city01": "燕京",
            "city02": "苏州",
            "city03": "金陵",
            "city04": "洛阳",
            "city05": "成都",
            "born01": "鸡鸣驿",
            "born02": "恶人谷",
            "born03": "烟雨庄",
            "born04": "千灯镇",
            "school01": "锦衣卫",
            "school02": "丐帮",
            "school03": "君子堂",
            "school04": "极乐谷",
            "school05": "唐门",
            "school06": "峨眉",
            "school07": "武当",
            "school08": "少林",
            "school09": "移花",
            "school10": "桃花",
            "school13": "血刀",
            "school14": "古墓",
            "school15": "念罗",
            "school17": "华山",
            "school18": "达摩",
            "school19": "神水",
            "school20": "明教",
            "school21": "神机",
            "school22": "天山",
            "school23": "星渺",
            "school24": "昆仑",
            "school25": "天涯",
            "school26": "刑天",
            "school28": "望辉",
            "scene08": "大漠",
            "scene25": "凌霄城",
        }
        asyncio.create_task(self.msg_tasks())
        logger.info("消息发送线程已启动")
        
    async def msg_tasks(self):
        """检查并执行到期的任务，每10秒检查一次"""
        while self.task_running:
            current_msgs = self.msgs.copy()
            for umo, umo_msg_list in current_msgs.items():
                if not umo_msg_list:
                    continue
                try:
                    for msg in umo_msg_list:
                        logger.info(f"发送消息到：{umo}, 消息内容：{msg}")
                        await self.context.send_message(umo, msg)
                    # 发送完成后清空该umo的消息列表
                    self.msgs[umo] = []
                except Exception as e:
                    logger.error(f"发送消息失败: {str(e)}")

            # 等待10秒再次检查
            await asyncio.sleep(3)
            
    def isInArea(self, x, y, x2, y2, r):
        """判断点(x, y)是否在以(x2, y2)为圆心，半径为r的圆内"""
        return (x - x2) ** 2 + (y - y2) ** 2 <= r ** 2
            
    def getPlaceDesc(self, scene, x, y):
        scene_name = self.scene_map.get(scene, None)
        if scene_name:
            area = ""
            x = int(x)
            y = int(y)
            if scene_name == "苏州":
                if self.isInArea(x, y, 284, 844, 100):
                    area = "【苏州后山】可能准备偷袭"
                if self.isInArea(x, y, 375, 755, 100):
                    area = "亦庄区域"
                if self.isInArea(x, y, 417, 924, 100):
                    area = "【风铃谷三岔路口】可能准备偷袭"
                if self.isInArea(x, y, 428, 629, 100):
                    area = "长风镖局"
                if self.isInArea(x, y, 486, 366, 100):
                    area = "【钱庄区域】"
                if self.isInArea(x, y, 501, 387, 100):
                    area = "【钱庄附近】可能要去仓库"
                if self.isInArea(x, y, 727, 617, 100):
                    area = "【苏州农田】可能在活动"
                if self.isInArea(x, y, 764, 475, 100):
                    area = "【苏州西门】可能从酒馆路过"
                if self.isInArea(x, y, 316, 442, 100):
                    area = "【清芳宫海阁出口】可能准备偷袭"
                if self.isInArea(x, y, 1487, 260, 100):
                    area = "【苏州枫晚林】如果今天是周六那就得小心了"

            elif scene_name == "烟雨庄":
                if self.isInArea(x, y, 116, 1358, 100):
                    area = "【盐帮】可能要去BOSS或者踢馆"
                if self.isInArea(x, y, 1053, 1312, 100):
                    area = "【断水崖驻地】可能要去打驻地"

            elif scene_name == "金陵":
                if self.isInArea(x, y, 361, 545, 100):
                    area = "【东郊拿草点】可能去开台子或者拿草(晚7.30)"
                if self.isInArea(x, y, 2079, 1796, 100):
                    area = "【金陵-成都门口】可能在运草"

            elif scene_name == "锦衣卫":
                if self.isInArea(x, y, 248, -74, 100):
                    area = "【授业点】肯定去授业"

            elif scene_name == "丐帮":
                if self.isInArea(x, y, 529, 414, 100):
                    area = "【授业点】肯定去授业"
                if self.isInArea(x, y, 578, 780, 100):
                    area = "【百兽庄门口】可能回势力或踢馆或BOSS"

            elif scene_name == "燕京":
                if self.isInArea(x, y, 359, 1252, 100):
                    area = "东方世家门口"

            elif scene_name == "鸡鸣驿":
                if self.isInArea(x, y, -80, 987, 100):
                    area = "【恶虎】可能BOSS或者踢馆"
                if self.isInArea(x, y, 411, 521, 100):
                    area = "【小鸡村心魔点】可能刚从家园出来或者刷心魔"
                if self.isInArea(x, y, 675, 379, 100):
                    area = "【小鸡村】可能要去铁匠或者换古谱"
                if self.isInArea(x, y, 749, 620, 100):
                    area = "【帮会战复活点】一般都是准备偷驻地"

            elif scene_name == "洛阳":
                if self.isInArea(x, y, 12, 478, 100):
                    area = "【抱犊寨】可能在踢馆"
                if self.isInArea(x, y, 523, 839, 100):
                    area = "【镖道-秦王府】可能在运镖"
                if self.isInArea(x, y, 814, 568, 100):
                    area = "【永夜城船夫】去永夜城"
                if self.isInArea(x, y, 1090, 666, 100):
                    area = "【钱庄附近】可能去仓库或准备拉镖"
                if self.isInArea(x, y, 1282, 447, 100):
                    area = "【授业区域】可能要授业"
                if self.isInArea(x, y, 919, 748, 100):
                    area = "【拉镖点附近】可能要拉镖"

            elif scene_name == "少林":
                if self.isInArea(x, y, 861, 442, 100):
                    area = "【授业点】肯定去授业"

            elif scene_name == "武当":
                if self.isInArea(x, y, 493, 279, 100):
                    area = "【授业点】肯定去授业"

            elif scene_name == "唐门":
                if self.isInArea(x, y, 686, 148, 100):
                    area = "【山脚豪杰】可能在刷豪杰"

            elif scene_name == "峨眉":
                if self.isInArea(x, y, 631, 305, 100):
                    area = "【授业点】肯定去授业"

            elif scene_name == "成都":
                if self.isInArea(x, y, 316, 804, 100):
                    area = "【金针】在日常或者交草"
                if self.isInArea(x, y, 564, 528, 100):
                    area = "【镖道】可能在抓人或运镖"
                if self.isInArea(x, y, 622, 1044, 100):
                    area = "【武侯祠】可能刷豪杰或帮会镖"
                if self.isInArea(x, y, 665, 289, 100):
                    area = "【徐家庄】可能在团练或者日常或者抓人"
                if self.isInArea(x, y, 715, 664, 100):
                    area = "【成都钱庄附近】可能去仓库"
                if self.isInArea(x, y, 767, 366, 100):
                    area = "【成都科玛集市】可能去千灯"
                if self.isInArea(x, y, 836, 673, 100):
                    area = "【授业点】肯定去授业"
                if self.isInArea(x, y, 983, 447, 100):
                    area = "【蟾岛】刷豪杰或者准备偷袭"

            elif scene_name == "千灯":
                if self.isInArea(x, y, 248, 675, 100):
                    area = "【千灯门口】准备偷袭或抢驻地"
                if self.isInArea(x, y, 377, 1021, 100):
                    area = "【天香茶林】在踢馆或者追击"
                if self.isInArea(x, y, 612, 646, 100):
                    area = "【千灯农田】可能在活动"
                if self.isInArea(x, y, 878, 745, 100):
                    area = "【千灯亦庄】可能要去打架"

            elif scene_name == "昆仑":
                if self.isInArea(x, y, 12, 193, 100):
                    area = "【天机小道】可能刷豪杰"

            elif scene_name == "恶人谷":
                if self.isInArea(x, y, 244, 805, 100):
                    area = "易容点"

            elif scene_name == "大漠":
                if self.isInArea(x, y, 1230, -189, 100):
                    area = "大漠家园附近"

                
            return f"{scene_name}-{area}"
        return scene
            
    def on_connect(self, client, context, flags, rc):
        """MQTT连接回调"""
        logger.info(f"Connected to MQTT broker with result code: {rc}")
        self.mqtt_client.subscribe(self.mqtt_topic)
    
    def on_message(self, client, context, msg):
        try:
            raw_message = msg.payload.decode('utf-8-sig')
            message = ''.join(char for char in raw_message if ord(char) >= 32 or char in ['\n', '\r']).strip()
            logger.info(f"Received MQTT message: topic = {msg.topic}, payload = {message}")
            if msg.topic == "game/player/info_update":
                # 遍历所有umo及其对应的targets
                for umo, targets in self.target_map.items():
                    for target in targets:
                        message_data = json.loads(message)
                        if target in message:
                            player_data = message_data["data"]
                            player_name = player_data["player_name"]
                            guild_name = player_data["guild_name"]
                            guild_position = player_data["guild_position"]
                            scene = player_data["scene"]
                            x = player_data["x"]
                            y = player_data["y"]
                            scene_name = self.getPlaceDesc(scene, x, y)
                            formatted_msg = f"发现213[{player_name}(帮会:{guild_name},职位:{guild_position})]出现在[{scene_name}],坐标为({x}, {y}),赶快去砍他啊,那个谁！淦！留着他过年？"
                            logger.info(f"发现目标：{target}, 需发送消息到：{umo}")
                            botmsg = MessageChain().message(formatted_msg)
                            if umo not in self.msgs:
                                self.msgs[umo] = []
                            self.msgs[umo].append(botmsg)
            else:
                logger.info(f"收到其他主题消息：{msg.topic}")
        except Exception as e:
            logger.error(f"处理MQTT消息时发生错误: {str(e)}")

    
    @event_message_type(EventMessageType.PRIVATE_MESSAGE)
    async def on_private_message(self, event: AstrMessageEvent):
        message_str = event.message_str # 获取消息的纯文本内容
    
    @llm_tool(name="suan_gua") 
    async def suan_gua(self, event: AstrMessageEvent, location: str) -> MessageEventResult:
        '''进行一次算卦，可以追踪一个目标的位置信息，持续10分钟。

        Args:
            targetname(string): 目标名字
        '''
        resp = "算卦成功，将会持续获得目标的位置信息，持续10分钟。"
        yield event.plain_result("算卦结果: " + resp)
    
    # 注册指令的装饰器。指令名为 helloworld。注册成功后，发送 `/helloworld` 就会触发这个指令，并回复 `你好, {user_name}!`
    @filter.command("发这里")
    async def zzplayer(self, event: AstrMessageEvent):
        '''发送目标坐标的群id,当用户发送"发这里 张三",系统收到张三的坐标信息,就将其发送到该用户会话''' # 这是 handler 的描述，将会被解析方便用户了解插件内容。建议填写。
        target = event.message_str.replace("发这里 ", "").strip()
        umo = event.unified_msg_origin
        
        # 初始化或添加新目标
        if umo not in self.target_map:
            self.target_map[umo] = set()
        self.target_map[umo].add(target)
        
        logger.info(f"添加追踪目标：{target}, 发送消息到：{umo}, 当前该会话追踪目标：{self.target_map[umo]}")
        yield event.plain_result(f"当前追踪目标：{self.target_map[umo]}")
        event.stop_event()
    
    @filter.command("停止")
    async def stopzz(self, event: AstrMessageEvent):
        '''停止追踪目标，当用户发送"停止 张三"时，停止追踪该目标。如果不指定目标，则停止所有追踪'''
        umo = event.unified_msg_origin
        target = event.message_str.replace("停止 ", "").strip()
        
        if umo not in self.target_map:
            logger.info(f"会话 {umo} 没有追踪任何目标")
            yield event.plain_result(f"会话 {umo} 没有追踪任何目标")
            return
        
        if target:
            # 删除指定目标
            if target in self.target_map[umo]:
                self.target_map[umo].remove(target)
                logger.info(f"已停止追踪目标：{target}, 当前该会话剩余追踪目标：{self.target_map[umo]}")
                yield event.plain_result(f"已停止追踪目标：{target}, 当前该会话剩余追踪目标：{self.target_map[umo]}")
            else:
                logger.info(f"目标 {target} 不在追踪列表中")
                yield event.plain_result(f"目标 {target} 不在追踪列表中")
        else:
            # 删除所有目标
            self.target_map[umo].clear()
            logger.info(f"已停止追踪所有目标，会话 {umo} 的追踪列表已清空")
            yield event.plain_result(f"已停止追踪所有目标，会话 {umo} 的追踪列表已清空")
            
        # 如果该会话没有追踪目标了，删除该会话的记录
        if not self.target_map[umo]:
            del self.target_map[umo]
        
        event.stop_event()
            
    # 注册指令的装饰器。指令名为 helloworld。注册成功后，发送 `/helloworld` 就会触发这个指令，并回复 `你好, {user_name}!`
    @filter.command("算卦")
    async def helloworld(self, event: AstrMessageEvent):
        '''算卦指令''' # 这是 handler 的描述，将会被解析方便用户了解插件内容。建议填写。
        user_name = event.get_sender_name()
        message_str = event.message_str.replace("算卦 ", "").strip() # 用户发的纯文本消息字符串
        message_chain = event.get_messages() # 用户所发的消息的消息链 # from astrbot.api.message_components import *
        logger.info(message_chain)
        logger.info(f"调用mqtt下发算卦命令：算卦目标={message_str}, 命令来源={user_name}")
        
        mqtt_payload = {
           "filename": "cn_logic\\\\cn_logic_mqtool", "method": "testRun",
            "args": f"{message_str},{self.config.get('sub_config').get('guashiname')}"
        }
        mqtt_payload = json.dumps(mqtt_payload)
        logger.info(f"mqtt send payload: {mqtt_payload}")
        self.mqtt_client.publish(self.config.get('sub_config').get('smalluser'), mqtt_payload)
        event.stop_event()
        # yield event.plain_result(f"Hello, {user_name}, 你发了 {message_str}!") # 发送一条纯文本消息

    async def terminate(self):
        '''可选择实现 terminate 函数，当插件被卸载/停用时会调用。'''
        self.task_running = False
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()