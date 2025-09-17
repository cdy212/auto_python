/************************* HappyTuk launcher *******************************************/
//Default State
var isTest = false;
var isSupported = false;
var protocol = "happytuk"
var gameName = '';

var hostname = window.location.hostname;

var DOMAINNAME = hostname;
var HOSTNAME = 'https://' + hostname;

var BROWSER_FIREFOX = 1;
var BROWSER_CHROME  = 2;
var BROWSER_IE      = 3;
var BROWSER_IE11	= 4;	// InternetExplorer11
var BROWSER_OTHER   = 5;
var BROWSER_EDGE   = 6;
var BROWSER_FIREFOX64   = 7;
var BROWSER_OPERA   = 8;

function detectedBrowser () {

	if (-1 != navigator.userAgent.indexOf("AppleWebKit") && -1 != navigator.userAgent.indexOf("OPR")) return BROWSER_OPERA;
	if (-1 != navigator.userAgent.indexOf("AppleWebKit") && -1 != navigator.userAgent.indexOf("Edge")) return BROWSER_EDGE;
	if (-1 != navigator.userAgent.indexOf("Firefox") && -1 != navigator.userAgent.indexOf("x64")) return BROWSER_FIREFOX64;

	if (-1 != navigator.userAgent.indexOf("Chrome")) return BROWSER_CHROME;
	if (-1 != navigator.userAgent.indexOf("Firefox")) return BROWSER_FIREFOX;
	if (-1 != navigator.userAgent.indexOf("MSIE ")) return BROWSER_IE;
	if (-1 != navigator.userAgent.indexOf("Trident/7.0")) return BROWSER_IE11;
	else return BROWSER_OTHER;
}

//Helper Methods
function getProtocol(){
	return protocol
}

function result(){
	if(!isSupported){
		alert("There is no HappyTuk Launcher.");
	}

}

function launchCheck(auth){
	auth = encodeURIComponent(auth);

	if(gameName === 'closers') {
		protocol = "naddiclauncherjpn";
	}

	if(gameName === 'clo') {
		protocol = "naddiclaunchertwn";
	}

	var url = getProtocol()+":"+auth;

	window.protocolCheck(url ,
		function () {
		});
	/*
	setTimeout(function() {
		//location.href = "/game/" + gameName +"/gamestart";
		//window.blur();
		//minimize();
		//if(hostname.indexOf('mangot5.com') != -1) $('#gameStartModal').modal('show');
	}, 1000);
   */
	var gpbtnel = $('.gamestart')[0];
	var isfocus = false;
	gpbtnel.focus();
	gpbtnel.onblur = function(){
		isfocus = true;
	};

	setTimeout(function(){
		var launcherDownloadMsg = "Launcher downloaded..." ;
		gpbtnel.onblur = null;
		if (!isfocus) {
			if(hostname.indexOf('.jp') != -1){
				launcherDownloadMsg ="【お知らせ】\n\nゲームを起動するには起動用のプログラムをインストールする必要があります。\n";
				if(confirm(launcherDownloadMsg)){
					//window.location.href = 'http://jp.mangot5.com/HappyTukLauncher_Setup_JP.exe';
					if(gname === 'closers') {
						window.location.href = 'https://patch-cls.happytuk.co.jp/closersjp/LAUNCHER/V2/Setup.exe';
					} else {
						window.location.href = 'https://images.happytuk.co.jp/htlauncher/HappyTukLauncher_Setup_JP.exe';
					}
				}else{
					// msg > need launcher install
					if(gameName !== 'closers') {
						window.location.href = $('#launcherGuideUrl').val();
					}

				}
			}else if(hostname.indexOf('mangot5.com') != -1) {
				launcherDownloadMsg ="[公告] 若要使用網頁啟動遊戲，須先安裝快樂玩啟動器。要進行下載嗎？";

				if(confirm(launcherDownloadMsg)){
					if(gname === 'clo') { /*TW closers 분기처리*/
						window.location.href = 'https://patch-cls.closers.com.tw/closerstw/LAUNCHER/V1/setup.exe';
					} else {
						window.location.href = 'https://image.mangot5.com/HappyTukLauncher_Setup.exe';
					}
				}else{
					if($('#launcherGuideUrl').val() == undefined)
						$('#gameStartModal').modal('show');
					else
						window.location.href = $('#launcherGuideUrl').val();
					// msg > need launcher install
				}
			}else if(hostname.indexOf('.th') != -1) {
				launcherDownloadMsg ="[ประกาศ] หากคุณต้องการเข้าสู่ระบบ คุณจำเป็นต้องดาวน์โหลดและติดตั้งโปรแกรม Launcher HappyTuk ก่อน ต้องการดาวน์โหลดหรือไม่?\n";

				if(confirm(launcherDownloadMsg)){
					window.location.href = 'https://image.happytuk.co.th/HappyTukLauncher_TH_Setup.exe';
				}else{
					if($('#launcherGuideUrl').val() == undefined)
						$('#gameStartModal').modal('show');
					else
						window.location.href = $('#launcherGuideUrl').val();
					// msg > need launcher install
				}
			}
		}
	}, 5000);
}

//Handle Firefox
function launchMozilla(auth){

	var url = getProtocol()+":"+auth,
		iFrame = $('#hiddenIframe')[0];

	isSupported = false;

	//Set iframe.src and handle exception
	try{
		iFrame.contentWindow.location.href = url;
		isSupported = true;
		result();
	}catch(e){
		//FireFox
		if (e.name == "NS_ERROR_UNKNOWN_PROTOCOL"){
			isSupported = false;
			result();
		}
	}
}

//Handle Chrome
function launchChrome(auth){

	var url = getProtocol()+":"+auth,
		protcolEl = $('#protocol')[0];

	isSupported = false;


	protcolEl.focus();
	protcolEl.onblur = function(){
		isSupported = true;
	};

	//will trigger onblur
	location.href = url;

	//Note: timeout could vary as per the browser version, have a higher value
	setTimeout(function(){
		protcolEl.onblur = null;
		result()
	}, 5000);

}
//Handle Other Browser
function otherBrowser(auth){
	var url = getProtocol()+":"+auth,
		protcolEl = $('#protocol')[0];
	location.href =  url;
}

function launcher_call(gname, userNo, mode, /** selective **/userId){
	var configUrl = DOMAINNAME+'/webLauncher/config';
	if(mode != 'LIVE') isTest = true;

	gameName = gname;

	var returnCode = -1;
	if (gameName == 'gs') {
		if (userNo == '') {
			alert('請先登錄。');
			return false;
		} else {
			returnCode = checkIngameAccount(gameName);
			if (returnCode == 0) {
				returnCode = createIngameAccount(gameName);
				if (returnCode == 0) {
					alert('請向客服人員詢問。['+returnCode+']');
					return false;
				}
			}
			if (returnCode != 1) {
				alert('請向客服人員詢問。['+returnCode+']');
				return false;
			}
		}
	} else if (gameName == 'rom') {
		/*returnCode = checkIp(gameName);
		if (returnCode == -1) {
			alert('【尚未開啟。敬請期待】');
			return false;
		}*/
		if (userNo == '') {
			alert('請先登入帳號。');
			return false;
		}
	}

	if(userNo == ''){
		launchCheck(gname + "| |"+isTest +'|'+ configUrl);
	}else{
		if (gameName == 'xa'){
			//소호강호 로직
			//1. 로그인 기록 처리 먼저
			$.ajax({
				type: "POST",
				url: "/game/"+gname+"/gameAuthLogin.json",
				async: false,
				success: function(data) {
					//returnCode == 1일때만 통과
					if(data.returnCode != 1){
						if(data.returnCode == 50000 || data.returnCode == 50011){
							alert("帳號密碼資訊不正確或無此帳號，請重新登入。")
							return false;
						}else if(data.returnCode == 50015 || data.returnCode == 50050){
							alert("當前帳號無法登入，請與客服中心聯繫。")
							return false;
						}else{
							alert("發生錯誤，請與客服中心聯繫。")
							return false;
						}
					}else{
						//2. ticket 발급
						var ticket = getRegistTicket();

						if(ticket.status != 1){
							if(ticket.status == 50000){
								alert("發生錯誤 \n 帳號密碼資訊不正確或無此帳號。" );
							}else if(ticket.status == 50400){
								alert('請向客服人員詢問。['+ticket.message +']');
							}else if(ticket.status == 50500){
								alert('發生錯誤 \n 請向客服人員詢問。');
							}
							return false;
						}else {
							//정상이면 launcher call
							var defaultParam = "user:" + userId + "@taiwan@sso" + " " + "pwd:" +ticket.message;
							// console.log(gname + "|"+defaultParam+"|"+isTest+'|'+ configUrl)
							launchCheck(gname + "|"+defaultParam+"|"+isTest+'|'+ configUrl);
						}
					}
				},
				error : function(data){
					alert("user data error ocurred. 請向客服人員詢問。")
					return false;
				}
			})
		} else {
			$.ajax({
				type: "POST",
				url: "/game/" + gname + "/getLauncherAuthKey.json",
				data: {userNo: userNo},
				async: false,
				success: function (data) {
					var defaultParam = data.userNo + " " + data.authKey;
					// authkey missmatch pre check
					if (data.authKey == null || data.authKey == "" || data.authKey.trim() == "" ) {
						if(hostname.indexOf('.jp') != -1) {
							if(confirm("再度ログインしてください。")) {
								location.href="/web/login?gname="+gname+"&ref="+window.location.pathname+window.location.search
							}
						} else {
							if(confirm("登入閒置時間過久，請重新登入。")) {
								location.href="/Index/Member/Login?gname="+gname+"&ref="+window.location.pathname+window.location.search
							}
						}
					} else {
						if (gameName == 'r2') {
							defaultParam = "/" + userId + "/" + data.userNo + "/" + data.authKey;
						} else if (gameName == 'au') {
							var userInfo = encodeURIComponent($('#userInfo').val());
							var mode = window.location.hostname.indexOf('au.') ? 'test' : 'live';
							var pathPath = encodeURIComponent('patch-au.mangot5.com.tw/audition_patch/patch/' + mode);
							defaultParam = defaultParam + ' ' + userInfo + ' ' + pathPath;
						} else if (gameName == 'gj') {
							defaultParam = "-account=" + data.userNo + " " + "-ticket=" + data.authKey;
						}

						if(gameName === 'closers'|| gameName === 'clo') {
							launchCheck(defaultParam);
						} else {
							launchCheck(gname + "|" + defaultParam + "|" + isTest + '|' + configUrl);
						}
					}
				},error: function (data) {
					console.log(data);
				}
			});
		}

	}
}
function launcher_call_as_web(gname, mode, sid, ip, userNo){
	$.ajax({
		type: "POST",
		url: "/game/"+gname+"/getAuthKey.json",
		data: {userNo:userNo},
		success: function(result){
			//result.authKey;
			if(gname == 'ro'){
				$.ajax({
					type: "POST",
					data:{sid:sid, ip:ip, mode:mode, authKey:result.authKey},
					url: "/ro/auth.json",
					success: function(data){
						//console.log(data);
						if(data.loginResult.Return){
							$('.webLauncher').show();
							$('#webLauncherFrame').attr('src', data.result);
							$('#wrapContainer, #wrap').hide();
							$('body').scrollTop(5000);
							//console.log(data.result);
						}
					},
					error : function(data){
					}
				});
			}
		},
		error : function(data){
			console.log(data);
		}
	});
}

// get ticket for xa
function getRegistTicket(){
	var ticket = {'status' : 1, 'message' : ''};
	$.ajax({
		type :"POST",
		url : "/" + gname + "/getRegistTicket.json",
		async : false,
		success : function(data){
			if(data.result.returnCode == 1){
				if(data.result.apiResultMsg && data.result.apiResultMsg != null &&  data.result.apiResultMsg != ''){
					ticket.status = 1;
					ticket.message = data.result.apiResultMsg;
				}else{
					// alert("error occur : " + data.result.result.message);
					ticket.status = 50000;
					ticket.message = data.result.apiResultMsg;
				}
			}else{
				ticket.status = 50400;
				ticket.message = data.result.returnCode;
			}
		},
		error : function(error){
			console.error("error occured :", error);
			ticket.status = 50500;
		}
	})
	return ticket;
}

function closeWebGame(){
	$('.webLauncher').hide();
	$('#webLauncherFrame').attr('src', '');
	$('#wrapContainer, #wrap').show();
	$('body').scrollTop(0);

	if (document.exitFullscreen) {
		document.exitFullscreen();
	} else if (document.msExitFullscreen) {
		document.msExitFullscreen();
	} else if (document.mozCancelFullScreen) {
		document.mozCancelFullScreen();
	} else if (document.webkitExitFullscreen) {
		document.webkitExitFullscreen();
	}
}
function minimize(){
	window.innerWidth=100;
	window.innerHeight=100;
	window.screenX = screen.width;
	window.screenY = screen.height;
	alwaysLowered = true;
}
function fullScreen(){
	//Toggle fullscreen off, activate it
	if (!document.fullscreenElement && !document.mozFullScreenElement && !document.webkitFullscreenElement && !document.msFullscreenElement ) {
		if (document.documentElement.requestFullscreen) {
			document.documentElement.requestFullscreen();
		} else if (document.documentElement.mozRequestFullScreen) {
			document.documentElement.mozRequestFullScreen(); // Firefox
		} else if (document.documentElement.webkitRequestFullscreen) {
			document.documentElement.webkitRequestFullscreen(); // Chrome and Safari
		} else if (document.documentElement.msRequestFullscreen) {
			document.documentElement.msRequestFullscreen(); // IE
		}

		//Toggle fullscreen on, exit fullscreen
	} else {

		if (document.exitFullscreen) {
			document.exitFullscreen();
		} else if (document.msExitFullscreen) {
			document.msExitFullscreen();
		} else if (document.mozCancelFullScreen) {
			document.mozCancelFullScreen();
		} else if (document.webkitExitFullscreen) {
			document.webkitExitFullscreen();
		}
	}
}

function checkIngameAccount(gname) {
	var resultCode = -1;
	$.ajax({
		type : 'POST',
		async : false,
		contentType : 'application/x-www-form-urlencoded; charset=UTF-8',
		url : "/" + gname + "/checkIngameAccount.json",
		success: function(data) {
			if (data != null) {
				resultCode = data.result;
			}
		}
	});
	return resultCode;
}

function createIngameAccount(gname) {
	var resultCode = -1;
	$.ajax({
		type : 'POST',
		async : false,
		contentType : 'application/x-www-form-urlencoded; charset=UTF-8',
		url : "/" + gname + "/createIngameAccount.json",
		success: function(data) {
			if (data != null) {
				resultCode = data.result;
			}
		}
	});
	return resultCode;
}

function checkIp(gname) {
	var resultCode = -1;
	$.ajax({
		type : 'POST',
		async : false,
		contentType : 'application/x-www-form-urlencoded; charset=UTF-8',
		url : "/" + gname + "/checkIp.json",
		success: function(data) {
			if (data != null) {
				resultCode = data.result;
			}
		}
	});
	return resultCode;

}