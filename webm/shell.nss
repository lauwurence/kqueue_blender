settings
{
	priority=1
	exclude.where = !process.is_explorer
	showdelay = 200
	// Options to allow modification of system items
	modify.remove.duplicate=1
	tip.enabled=true
}

import 'imports/theme.nss'
import 'imports/images.nss'

import 'imports/modify.nss'

menu(mode="multiple" title="Pin/Unpin" image=icon.pin)
{
}

menu(mode="multiple" title=title.more_options image=icon.more_options)
{
}

item(
	title='Convert to WebM 1080p'
	cmd='F:\RenPy\00_Renders\kqueue_blender\webm\.webm - 1080p.bat'
	dir='F:\RenPy\00_Renders\kqueue_blender\webm\'
	arg='@sel.path'
	image='cmd.exe'
	separator=true
	pos=1
	separator='before')

item(
	title='Convert to WebM android'
	cmd='F:\RenPy\00_Renders\kqueue_blender\webm\.webm - android.bat'
	dir='F:\RenPy\00_Renders\kqueue_blender\webm\'
	arg='@sel.path'
	image='cmd.exe'
	pos=2)

item(
	title='Convert to WebM 2160p'
	cmd='F:\RenPy\00_Renders\kqueue_blender\webm\.webm - 2160p.bat'
	dir='F:\RenPy\00_Renders\kqueue_blender\webm\'
	arg='@sel.path'
	image='cmd.exe'
	pos=3
	separator='after')
