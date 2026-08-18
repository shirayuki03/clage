# Clage

Clage is a Clambon Web extension for making Canvas games.

## Load in Clambon Web

Manifest URL:

https://raw.githubusercontent.com/shirayuki03/clage/main/extension.json

## Example

```clambon
import Clage

Stage() {
  run()
}

Sprite(Player) {
  start {
    Player.costume = "player.png"
    Player.x = 0
    Player.y = 0
  }
}
